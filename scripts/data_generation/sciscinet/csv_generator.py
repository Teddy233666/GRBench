import os
import numpy
import pandas
import duckdb
import pyarrow as pa
import tempfile
import shutil
import subprocess
from ScaleMap import scale_map as sm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DATA_SOURCE = os.environ.get(
    "SCISCINET_PARQUET_ROOT", os.path.join(REPO_ROOT, "data", "raw", "sciscinet-v2")
)
DATA_DESTINATION = os.environ.get(
    "SCISCINET_CSV_ROOT", os.path.join(REPO_ROOT, "data", "processed", "sf10_4")
)
GRBENCH_DATA_ROOT = os.environ.get(
    "GRBENCH_DATA_ROOT", os.path.join(REPO_ROOT, "data", "processed")
)

class csv:
    def __init__(self):
        self.data_source = DATA_SOURCE
        self.data_destination = DATA_DESTINATION
        os.makedirs(self.data_destination, exist_ok=True)

        self.sm = sm(GRBENCH_DATA_ROOT)


    # transfer the original parquet files to the csv files
    def parquet2csv(self):
        # get all .parquet files
        redundant_files = ["funders.parquet",
                           "papers_raw.parquet",
                           "sciscinet_authors_bq.parquet",
                           "sciscinet_papers_pmid_pmcid.parquet",
                           "sciscinet_papertitleabstract.parquet",
                           "sciscinet_paper_author_affiliation.parquet"]
        parquet_files = [
            f for f in os.listdir(self.data_source)
            if f.endswith(".parquet") and f not in redundant_files
        ]
        # parquet_files = ['sciscinet_affl_assoc_affl.parquet']

        if not parquet_files:
            print("No parquet files found.")
            return

        print(f"Found {len(parquet_files)} parquet files.")

        for idx, fname in enumerate(parquet_files):
            src_path = os.path.join(self.data_source, fname)
            dest_path = os.path.join(self.data_destination, fname.replace(".parquet", ".csv"))

            print(f"\n[{idx+1}/{len(parquet_files)}] Converting: {fname}")

            # DuckDB connection
            con = duckdb.connect()

            # Get row count (DuckDB count is fast with Parquet metadata)
            total_rows = con.execute(
                f"SELECT COUNT(*) FROM parquet_scan('{src_path}')"
            ).fetchone()[0]
            print(f"Total rows: {total_rows}")

            # The streaming reader
            chunk_size = 50000
            batch_stream = con.execute(
                f"SELECT * FROM parquet_scan('{src_path}')"
            ).fetch_record_batch(chunk_size)

            first_write = True
            processed = 0

            while True:
                try:
                    batch = batch_stream.read_next_batch()
                except StopIteration:
                    break

                if batch is None:
                    break

                # Convert Arrow batch → pandas → CSV
                df = batch.to_pandas()

                df.to_csv(dest_path,
                        mode='w' if first_write else 'a',
                        header=first_write,
                        index=False)

                first_write = False
                processed += len(df)

                # Periodically print progress (per 5 chunks)
                if processed == len(df) or processed % (chunk_size * 5) == 0:
                    print(f"Processed: {processed}/{total_rows}")

            print(f"Finished: {fname} → {dest_path}")


    # a counter to get the line number of each file
    def counter(self):
        redundant_files = ["funders.parquet",
                           "papers_raw.parquet",
                           "sciscinet_authors_bq.parquet",
                           "sciscinet_papers_pmid_pmcid.parquet",
                           "sciscinet_papertitleabstract.parquet"]
        parquet_files = [
            f for f in os.listdir(self.data_source)
            if f.endswith(".parquet") and f not in redundant_files
        ]
        parquet_files = ["sciscinet_paper_author_affiliation.parquet"]

        if not parquet_files:
            print("No parquet files found.")
            return

        print(f"Found {len(parquet_files)} parquet files.")

        for idx, fname in enumerate(parquet_files):
            src_path = os.path.join(self.data_source, fname)
            dest_path = os.path.join(self.data_destination, fname.replace(".parquet", ".csv"))

            # print(f"\n[{idx+1}/{len(parquet_files)}] Converting: {fname}")

            con = duckdb.connect()

            total_rows = con.execute(
                f"SELECT COUNT(*) FROM parquet_scan('{src_path}')"
            ).fetchone()[0]
            print(f"Total rows: {total_rows} (file: {fname})")


    # remove invalid items in sciscinet_paper_author_affiliation.csv
    def clean_paper_affi(self):
        src_parquet = os.path.join(self.data_source, "sciscinet_paper_author_affiliation.parquet")
        dst_csv = os.path.join(self.data_destination, "sciscinet_paper_author_affiliation.csv")

        con = duckdb.connect()

        try:
            print("Step 1: Loading parquet into DuckDB table...")

            # read all the data in .parquet file
            con.execute("""
                CREATE OR REPLACE TABLE paper_author_affi AS
                SELECT *
                FROM read_parquet(?)
            """, [src_parquet])

            print("Step 2: Deleting rows with empty institutionid...")
            # delete all the invalid items
            con.execute("""
                DELETE FROM paper_author_affi
                WHERE institutionid IS NULL
                OR institutionid = ''
            """)

            print("Step 3: Exporting cleaned data to CSV...")
            #  write the result in a csv file
            con.execute(f"""
                COPY paper_author_affi
                TO '{dst_csv}'
                (HEADER, DELIMITER ',')
            """)

            print("Done: sciscinet_paper_author_affiliation cleaned successfully.")

        finally:
            con.close()


    # create author affiliation
    def create_author_affiliation(self):
        src_parquet = os.path.join(self.data_source, "sciscinet_paper_author_affiliation.parquet")
        dst_csv = os.path.join(self.data_destination, "sciscinet_author_affiliation.csv")

        os.makedirs(os.path.dirname(dst_csv), exist_ok=True)

        if os.path.exists(dst_csv):
            os.remove(dst_csv)

        con = duckdb.connect()

        try:
            print("[Step 1] Loading parquet into DuckDB table...")

            # read all the data in .parquet file
            con.execute("""
                CREATE OR REPLACE TABLE paper_author_affi AS
                SELECT institutionid, author_position, authorid
                FROM read_parquet(?)
                WHERE institutionid IS NOT NULL AND institutionid != ''
            """, [src_parquet])

            print("[Step 2] Exporting selected data to CSV...")
            #  write the result in a csv file
            con.execute(f"""
                COPY paper_author_affi
                TO '{dst_csv}'
                (HEADER, DELIMITER ',')
            """)

            result = con.execute(f"""
                SELECT COUNT(*)
                FROM read_csv_auto(
                    '{dst_csv}',
                    header=true,
                    strict_mode=false
                )
            """).fetchone()
            print(f"[INFO] sciscinet_author_affiliation row count: {result[0]}")

            print("Done.\n")

        finally:
            con.close()


    def update_institutionid(self, file_name):
        path = os.path.join(self.data_destination, file_name)

        if not os.path.exists(path):
            raise FileNotFoundError(path)

        with open(path, "r", encoding="utf-8") as f:
            header = f.readline()
            rest_pos = f.tell()

        if "institutionid" in header:
            print("[INFO] header already correct, skip.")
            return

        subprocess.run(
            ["sed", "-i", "1s/^institution_id,/institutionid,/", path],
            check=True
        )
        print(f"[INFO] Updated header safely: {file_name}")



if __name__ == "__main__":
    gen = csv()
    gen.parquet2csv()
    gen.clean_paper_affi()

    gen.create_author_affiliation()
    gen.update_institutionid("sciscinet_affl_assoc_affl.csv")
    gen.update_institutionid("sciscinet_affiliations.csv")

    # gen.counter()
