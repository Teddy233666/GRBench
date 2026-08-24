import duckdb
import os

class scale_map:
    def __init__(self, path):
        self.path = path

    # get the path to data dir via the scale factor
    def get_data_path(self, sf:int):
        return os.path.join(self.path, "sf10_" + str(sf))

    # counter the row number of a csv file
    def csv_counter(self, csv_path):
        print(f"Counting file: {csv_path}")

        con = duckdb.connect(database=':memory:')

        query = f"""
        SELECT COUNT(*)
        FROM read_csv_auto('{csv_path}', header=true, strict_mode=false, ignore_errors=true)
        """
        print(f"Total rows: {con.execute(query).fetchone()[0]}\n")


    def locate_bad_csv_line(self, csv_path):
        con = duckdb.connect(database=':memory:')
        try:
            con.execute(f"""
                SELECT 1 FROM read_csv_auto(
                    '{csv_path}',
                    header=true,
                    strict_mode=true
                )
            """)
        except Exception as e:
            print("CSV parsing failed:")
            print(e)
        finally:
            con.close()
