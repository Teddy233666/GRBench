import csv
import plyvel
import os
import sys
import resource
from pathlib import Path
from typing import Dict

class PaperIdFilter:
    """

    """
    def __init__(self,
                 csv_path: str,
                 paper_db_path: str,
                 paper_field: str = "paperid"):

        self.csv_path = Path(csv_path)
        self.paper_db_path = paper_db_path
        self.paper_field = paper_field

        # ✅ 输出文件名：原文件名 + _clean.csv
        original_stem = self.csv_path.stem
        output_filename = f"{original_stem}_clean.csv"
        self.output_csv_path = Path("legacy_host_data/grbench/sf10_1_postgresql") / output_filename

        self.valid_paper_ids: Dict[str, str] = {}

    def _load_valid_paper_ids(self) -> Dict[str, str]:
        if not os.path.exists(self.paper_db_path):
            raise FileNotFoundError(f"Paper哈希表不存在: {self.paper_db_path}")

        valid_ids = {}
        try:
            db = plyvel.DB(self.paper_db_path)
            for hash_id_bytes, paperid_bytes in db.iterator():
                try:
                    paperid = paperid_bytes.decode('utf-8').strip()
                    hash_id = hash_id_bytes.decode('utf-8').strip()
                    if paperid:
                        valid_ids[paperid] = hash_id
                except:
                    continue
            db.close()
            return valid_ids
        except Exception as e:
            raise RuntimeError(f"读取哈希表失败: {str(e)}")

    def load_mappings(self):
        print("📥 加载 paperid 映射表...")
        self.valid_paper_ids = self._load_valid_paper_ids()
        print(f"✅ 有效 paperid 数量: {len(self.valid_paper_ids):,}")

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

        print(f"🚀 开始过滤: {self.csv_path.name}")
        print(f"📤 输出到: {self.output_csv_path.name}")

        with open(self.csv_path, 'r', encoding=encoding, newline='') as infile, \
             open(self.output_csv_path, 'w', encoding='utf-8', newline='') as outfile:

            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                total += 1
                pid = row.get(self.paper_field, "").strip()

                if pid in self.valid_paper_ids:
                    writer.writerow(row)
                    kept += 1
                else:
                    dropped += 1

                if total % batch_size == 0:
                    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                    print(f"处理: {total:,} | 保留: {kept:,} | 丢弃: {dropped:,} | 内存: {mem:.1f}MB")

        print("\n" + "="*70)
        print(f"✅ 过滤完成！")
        print(f"📊 总行数: {total:,}")
        print(f"✅ 保留有效行: {kept:,}")
        print(f"🗑️ 丢弃无效行: {dropped:,}")
        print(f"📁 输出文件: {self.output_csv_path}")
        print("="*70)

if __name__ == "__main__":
    try:
        filter = PaperIdFilter(
            csv_path="legacy_host_data/grbench/sf10_1/hit_papers_level1.csv",
            paper_db_path="legacy_host_data/grbench/sf10_1_postgresql/sciscinet_papers",
            paper_field="paperid"
        )
        filter.load_mappings()
        filter.filter_csv()
    except Exception as e:
        print(f"❌ 错误: {str(e)}", file=sys.stderr)
        sys.exit(1)