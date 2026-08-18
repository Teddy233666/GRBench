import csv

input_path = "legacy_core/test/grbench_update6_papers_to_authors.csv"
output_path = "legacy_core/test/duckdb_copy/grbench_update5_papers_to_authors.csv"

with open(input_path, "r", newline="", encoding="utf-8") as fin, \
     open(output_path, "w", newline="", encoding="utf-8") as fout:

    reader = csv.reader(fin)
    writer = csv.writer(fout)

    for row in reader:
        # 去掉第一列
        writer.writerow(row[2:])