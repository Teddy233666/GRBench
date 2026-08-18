import csv
import plyvel
import os
import sys
import resource
from pathlib import Path
from typing import Dict

class PaperSourceFilter:
    """
    同时校验 paperid 和 sourceid 都存在于对应的哈希表中
    都存在 → 保留
    任意不存在 → 丢弃
    不生成任何额外列
    """
    def __init__(self,
                 csv_path: str,
                 paper_db_path: str,
                 source_db_path: str,
                 paper_field: str = "paperid",
                 source_field: str = "sourceid"):

        self.csv_path = Path(csv_path)
        self.paper_db_path = paper_db_path
        self.source_db_path = source_db_path
        self.paper_field = paper_field
        self.source_field = source_field

        # 输出文件名：原文件名_clean.csv
        original_stem = self.csv_path.stem
        output_filename = f"{original_stem}_clean.csv"
        self.output_csv_path = Path("legacy_host_data/grbench/sf10_1_postgresql") / output_filename

        self.valid_paper_ids: Dict[str, str] = {}
        self.valid_source_ids: Dict[str, str] = {}

    def _load_id_map(self, db_path: str, name: str) -> Dict[str, str]:
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"{name} 哈希表不存在: {db_path}")

        id_map = {}
        try:
            db = plyvel.DB(db_path)
            for key_bytes, val_bytes in db.iterator():
                try:
                    val = val_bytes.decode('utf-8').strip()
                    key = key_bytes.decode('utf-8').strip()
                    if val:
                        id_map[val] = key
                except:
                    continue
            db.close()
            print(f"✅ 加载 {name} 完成：{len(id_map):,} 条")
            return id_map
        except Exception as e:
            raise RuntimeError(f"加载 {name} 失败: {str(e)}")

    def load_mappings(self):
        print("\n📥 开始加载哈希表...")
        self.valid_paper_ids = self._load_id_map(self.paper_db_path, "Papers")
        self.valid_source_ids = self._load_id_map(self.source_db_path, "Sources")

    def filter_csv(self, batch_size: int = 500_000):
        if not self.csv_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.csv_path}")

        self.output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                f.read(1024)
            encoding = 'utf-8'
        except:
            encoding = 'latin-1'
            print(f"⚠️ 使用编码: {encoding}")

        total = 0
        kept = 0
        dropped = 0

        print(f"\n🚀 开始过滤: {self.csv_path.name}")
        print(f"✅ 规则：paperid + sourceid 必须都存在才保留")
        print(f"📤 输出: {self.output_csv_path.name}")

        with open(self.csv_path, 'r', encoding=encoding, newline='') as infile, \
             open(self.output_csv_path, 'w', encoding='utf-8', newline='') as outfile:

            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                total += 1
                pid = row.get(self.paper_field, "").strip()
                sid = row.get(self.source_field, "").strip()

                # ===================== 核心判断 =====================
                if pid in self.valid_paper_ids and sid in self.valid_source_ids:
                    writer.writerow(row)
                    kept += 1
                else:
                    dropped += 1

                if total % batch_size == 0:
                    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                    print(f"处理: {total:,} | 保留: {kept:,} | 丢弃: {dropped:,} | 内存: {mem:.1f}MB")

        print("\n" + "="*80)
        print(f"✅ 过滤完成！")
        print(f"总行数: {total:,}")
        print(f"保留有效行: {kept:,} （paperid + sourceid 都存在）")
        print(f"丢弃无效行: {dropped:,}")
        print(f"输出文件: {self.output_csv_path}")
        print("="*80)

if __name__ == "__main__":
    try:
        filter = PaperSourceFilter(
            csv_path="legacy_host_data/grbench/sf10_1/sciscinet_papersources.csv",
            paper_db_path="legacy_host_data/grbench/sf10_1_postgresql/sciscinet_papers",
            source_db_path="legacy_host_data/grbench/sf10_1_postgresql/sciscinet_sources",
            paper_field="paperid",
            source_field="sourceid"
        )
        filter.load_mappings()
        filter.filter_csv()
    except Exception as e:
        print(f"❌ 错误: {str(e)}", file=sys.stderr)
        sys.exit(1)