import csv
import plyvel
import os
import sys
import resource
from pathlib import Path
from typing import Dict


class RelationMapper:
    """
    通用关联表处理工具：
    新增4列：
        start_id
        start_vertex_type
        end_id
        end_vertex_type
    """

    def __init__(
        self,
        csv_path: str,
        start_db_path: str,
        end_db_path: str,
        start_field: str,
        end_field: str,
        start_vertex_value: str,
        end_vertex_value: str
    ):

        # 输入CSV
        self.csv_path = Path(csv_path)

        # 输出CSV（避免覆盖原文件）
        self.output_csv_path = (
            self.csv_path.parent /
            f"{self.csv_path.stem}_mapped.csv"
        )

        # LevelDB路径
        self.start_db_path = start_db_path
        self.end_db_path = end_db_path

        # 字段名
        self.start_field = start_field
        self.end_field = end_field

        # 固定类型值
        self.start_vertex_value = start_vertex_value
        self.end_vertex_value = end_vertex_value

        # 映射缓存
        self.start_field_to_id: Dict[str, str] = {}
        self.end_field_to_id: Dict[str, str] = {}

    def _reverse_leveldb_mapping(self, db_path: str) -> Dict[str, str]:
        """
        构建:
            value -> graphid
        """

        reverse_map = {}

        if not os.path.exists(db_path):
            raise FileNotFoundError(f"LevelDB不存在: {db_path}")

        try:
            # readonly=True 避免LOCK问题
            db = plyvel.DB(db_path, create_if_missing=False)

            for key_bytes, value_bytes in db.iterator():
                try:
                    graphid = key_bytes.decode("utf-8")
                    ext_id = value_bytes.decode("utf-8")

                    reverse_map[ext_id] = graphid

                except UnicodeDecodeError:
                    continue

            db.close()

            print(
                f"✅ 成功加载映射: {db_path} "
                f"| 条目数: {len(reverse_map):,}"
            )

            return reverse_map

        except Exception as e:
            raise RuntimeError(
                f"读取LevelDB失败: {db_path}\n错误: {str(e)}"
            )

    def load_mappings(self):

        print("📥 开始加载哈希表映射关系...")

        self.start_field_to_id = self._reverse_leveldb_mapping(
            self.start_db_path
        )

        self.end_field_to_id = self._reverse_leveldb_mapping(
            self.end_db_path
        )

    def process_csv(
        self,
        batch_size: int = 1_000_000,
        new_cols_position: str = "front"
    ):

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"CSV不存在: {self.csv_path}"
            )

        # 检测编码
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                f.read(1024)

            encoding = "utf-8"

        except UnicodeDecodeError:
            encoding = "latin-1"
            print(f"⚠️ 使用编码: {encoding}")

        processed_rows = 0
        missing_start = 0
        missing_end = 0

        print(f"🚀 开始处理CSV: {self.csv_path}")
        print(f"📁 输出文件: {self.output_csv_path}")

        with open(
            self.csv_path,
            "r",
            encoding=encoding,
            newline=""
        ) as infile, open(
            self.output_csv_path,
            "w",
            encoding="utf-8",
            newline=""
        ) as outfile:

            reader = csv.DictReader(infile)

            # 检查header
            if reader.fieldnames is None:
                raise ValueError(
                    "CSV header读取失败，请检查文件是否为空"
                )

            print(f"📌 检测到字段: {reader.fieldnames}")

            if self.start_field not in reader.fieldnames:
                raise ValueError(
                    f"CSV不存在字段: {self.start_field}"
                )

            if self.end_field not in reader.fieldnames:
                raise ValueError(
                    f"CSV不存在字段: {self.end_field}"
                )

            # 新增列
            new_cols = [
                "start_id",
                "start_vertex_type",
                "end_id",
                "end_vertex_type"
            ]

            # 字段顺序
            if new_cols_position == "front":
                new_fieldnames = new_cols + reader.fieldnames
            else:
                new_fieldnames = reader.fieldnames + new_cols

            writer = csv.DictWriter(
                outfile,
                fieldnames=new_fieldnames
            )

            writer.writeheader()

            for row in reader:

                # start
                start_ext_id = row.get(self.start_field, "")

                start_graphid = self.start_field_to_id.get(
                    start_ext_id,
                    ""
                )

                if not start_graphid:
                    missing_start += 1

                # end
                end_ext_id = row.get(self.end_field, "")

                end_graphid = self.end_field_to_id.get(
                    end_ext_id,
                    ""
                )

                if not end_graphid:
                    missing_end += 1

                # 新列
                row["start_id"] = start_graphid
                row["start_vertex_type"] = self.start_vertex_value

                row["end_id"] = end_graphid
                row["end_vertex_type"] = self.end_vertex_value

                writer.writerow(row)

                processed_rows += 1

                if processed_rows % batch_size == 0:

                    mem_mb = (
                        resource.getrusage(
                            resource.RUSAGE_SELF
                        ).ru_maxrss / 1024
                    )

                    print(
                        f"✅ 已处理: {processed_rows:,} 行 "
                        f"| 内存: {mem_mb:.2f} MB "
                        f"| 缺失start: {missing_start:,} "
                        f"| 缺失end: {missing_end:,}"
                    )

        print("\n" + "=" * 80)

        print(f"✅ 处理完成")
        print(f"📊 总行数: {processed_rows:,}")
        print(f"❌ 缺失start映射: {missing_start:,}")
        print(f"❌ 缺失end映射: {missing_end:,}")
        print(f"📁 输出文件: {self.output_csv_path}")

        print("=" * 80)


# =========================================================
# 主程序
# =========================================================

if __name__ == "__main__":

    # 输入CSV
    CSV_FILE_PATH = (
        "legacy_core/temp/"
        "grbench_update2_edges_with_types.csv"
    )

    # LevelDB
    START_DB_PATH = (
        "legacy_host_data/grbench/sf10_0_postgresql/"
        "sciscinet_papers_hash"
    )

    END_DB_PATH = (
        "legacy_host_data/grbench/sf10_0_postgresql/"
        "sciscinet_papers_hash"
    )

    # CSV字段名
    START_FIELD = "citing_paperid"
    END_FIELD = "cited_paperid"

    # 顶点类型
    START_VERTEX_VALUE = "Papers"
    END_VERTEX_VALUE = "Papers"

    # batch
    BATCH_SIZE = 1_000_000

    try:

        mapper = RelationMapper(
            csv_path=CSV_FILE_PATH,
            start_db_path=START_DB_PATH,
            end_db_path=END_DB_PATH,
            start_field=START_FIELD,
            end_field=END_FIELD,
            start_vertex_value=START_VERTEX_VALUE,
            end_vertex_value=END_VERTEX_VALUE
        )

        mapper.load_mappings()

        mapper.process_csv(
            batch_size=BATCH_SIZE,
            new_cols_position="front"
        )

    except Exception as e:

        print(
            f"\n❌ 程序执行失败:\n{str(e)}",
            file=sys.stderr
        )

        sys.exit(1)