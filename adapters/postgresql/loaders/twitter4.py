"""对 backup.sql 导出的顶点 CSV 仅将 id 列做 AGE graphid 低 48 位掩码。

当前只处理：
- grbench_update1_papers
- grbench_update6_authors_gender
"""

from __future__ import annotations

import pathlib

import pandas as pd

INPUT_DIR = pathlib.Path("legacy_core/test")
OUTPUT_DIR = pathlib.Path("legacy_core/temp")

MASK = (1 << 48) - 1

BASENAMES = (
    "grbench_update1_papers",
    "grbench_update6_authors_gender",
)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for basename in BASENAMES:
        input_path = INPUT_DIR / basename
        output_path = OUTPUT_DIR / f"{basename}_id_masked.csv"
        df = pd.read_csv(input_path)
        df["id"] = pd.to_numeric(df["id"], errors="raise").astype("int64") & MASK
        df.to_csv(output_path, index=False)
        print(f"已生成文件: {output_path}")


if __name__ == "__main__":
    main()
