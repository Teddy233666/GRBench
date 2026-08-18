import csv
import plyvel
import os
import sys
import resource
from pathlib import Path
from typing import Optional

class LargeCSVIdMapper:
    """
    处理亿级行CSV文件，添加自增ID并构建LevelDB持久化哈希表（id -> 自定义主键）
    """
    def __init__(self, csv_path: str, db_path: str = "./sciscinet_authors", primary_key: str = "paperid"):
        self.csv_path = Path(csv_path)
        self.db_path = Path(db_path)
        self.primary_key = primary_key  # 核心：将主键字段设为可配置变量
        # 输出CSV文件路径（根据原始文件名自动生成，也可自定义）
        self.output_csv_path = Path("legacy_host_data/grbench/sf10_4_postgresql") / self.csv_path.name
        self.db: Optional[plyvel.DB] = None

        # 优化LevelDB配置（针对亿级数据）
        self.leveldb_options = {
            'create_if_missing': True,
            'write_buffer_size': 64 * 1024 * 1024,  # 写缓冲区64MB
            'max_open_files': 1000,                  # 最大打开文件数
            'lru_cache_size': 32 * 1024 * 1024,       # 读缓存32MB
            'compression': 'snappy'                  # 启用snappy压缩
        }

    def __enter__(self):
        """上下文管理器，自动打开/关闭数据库"""
        # 确保哈希表目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = plyvel.DB(str(self.db_path), **self.leveldb_options)
        # 设置内存限制（防止OOM，根据服务器配置调整）
        resource.setrlimit(resource.RLIMIT_AS, (40 * 1024 * 1024 * 1024, -1))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
        if exc_type:
            print(f"❌ 处理出错: {exc_val}", file=sys.stderr)
            return False
        return True

    def process_csv(self, batch_size: int = 1_000_000):
        """
        处理CSV文件，添加自增ID并写入LevelDB
        :param batch_size: 批次大小（每处理N行打印进度）
        """
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV文件不存在: {self.csv_path}")

        # 确保输出CSV目录存在
        self.output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        # 预检查文件编码（避免读取失败）
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                f.read(1024)
            encoding = 'utf-8'
        except UnicodeDecodeError:
            encoding = 'latin-1'
            print(f"⚠️  UTF-8解码失败，使用 {encoding} 编码读取")

        # 逐行处理CSV（核心：不加载全量数据到内存）
        with open(self.csv_path, 'r', encoding=encoding, newline='') as infile, \
             open(self.output_csv_path, 'w', encoding='utf-8', newline='') as outfile:

            # 初始化CSV读写器
            reader = csv.DictReader(infile)

            # 检查主键字段是否存在
            if self.primary_key not in reader.fieldnames:
                raise ValueError(f"❌ CSV中不存在指定的主键字段: {self.primary_key}")

            # 将'id'添加到原有字段名列表的最前面
            fieldnames = ['id'] + reader.fieldnames
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            # 初始化计数器
            current_id = 1
            batch_counter = 0
            total_rows = 0

            # 批量写入LevelDB（减少磁盘IO次数，提升性能）
            write_batch = self.db.write_batch()

            for row in reader:
                # 1. 添加自增ID
                row['id'] = current_id
                # 2. 写入CSV
                writer.writerow(row)
                # 3. 批量写入LevelDB（使用配置的主键字段）
                primary_value = row[self.primary_key]
                write_batch.put(str(current_id).encode(), primary_value.encode())

                # 4. 批次处理逻辑
                current_id += 1
                batch_counter += 1
                total_rows += 1

                # 每处理batch_size行，提交批次并打印进度
                if batch_counter >= batch_size:
                    write_batch.write()  # 提交批量写入
                    write_batch = self.db.write_batch()  # 重置批次

                    # 打印进度和资源使用
                    mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
                    print(f"✅ 已处理: {total_rows:,} 行 | 内存占用: {mem_usage:.2f} MB | 当前ID: {current_id-1:,}")
                    batch_counter = 0

            # 提交最后一批数据
            if batch_counter > 0:
                write_batch.write()

        # 最终统计
        mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        # 计算哈希表磁盘占用（处理空目录情况）
        if self.db_path.exists() and os.listdir(self.db_path):
            db_size = sum(os.path.getsize(os.path.join(self.db_path, f)) for f in os.listdir(self.db_path)) / (1024**3)  # GB
        else:
            db_size = 0.0
        print("\n" + "="*50)
        print(f"📊 处理完成！总计行数: {total_rows:,}")
        print(f"📁 新CSV文件: {self.output_csv_path}")
        print(f"🗂️  LevelDB哈希表路径: {self.db_path}")
        print(f"🗂️  LevelDB数据库大小: {db_size:.2f} GB")
        print(f"🔑 映射关系: id -> {self.primary_key}")
        print(f"🚀 峰值内存占用: {mem_usage:.2f} MB")
        print("="*50)

    def query_mapping(self, target_id: int) -> Optional[str]:
        """
        查询ID对应的主键值（演示哈希表使用方式）
        :param target_id: 要查询的自增ID
        :return: 对应的主键值，不存在返回None
        """
        if not self.db:
            raise RuntimeError("数据库未打开")

        primary_value_bytes = self.db.get(str(target_id).encode())
        return primary_value_bytes.decode() if primary_value_bytes else None

# ------------------- 主程序入口 -------------------
if __name__ == "__main__":
    # ===================== 配置区（只需修改这里即可适配不同文件）=====================
    # 示例1：处理sciscinet_authors.csv（主键为authorid）
    # CSV_FILE_PATH = "legacy_host_data/grbench/sf10_4/sciscinet_authors.csv"
    # LEVELDB_PATH = "legacy_host_data/grbench/sf10_4_postgresql/sciscinet_authors_hash"
    # PRIMARY_KEY = "authorid"  # 自定义主键字段

    # 示例2：处理sciscinet_papers.csv（主键为paperid）
    CSV_FILE_PATH = "legacy_host_data/grbench/sf10_4/sciscinet_papers.csv"
    LEVELDB_PATH = "legacy_host_data/grbench/sf10_4_postgresql/sciscinet_papers"
    PRIMARY_KEY = "paperid"  # 自定义主键字段

    # ===================== 无需修改下面的代码 =====================
    try:
        with LargeCSVIdMapper(
            csv_path=CSV_FILE_PATH,
            db_path=LEVELDB_PATH,
            primary_key=PRIMARY_KEY
        ) as mapper:
            # 处理CSV（批次大小设为100万行，可根据服务器性能调整）
            mapper.process_csv(batch_size=1_000_000)

            # 示例：查询ID=1对应的主键值（验证映射关系）
            sample_id = 1
            sample_primary_value = mapper.query_mapping(sample_id)
            print(f"\n🔍 示例查询：ID={sample_id} -> {PRIMARY_KEY}={sample_primary_value}")

    except Exception as e:
        print(f"❌ 程序执行失败: {str(e)}", file=sys.stderr)
        sys.exit(1)