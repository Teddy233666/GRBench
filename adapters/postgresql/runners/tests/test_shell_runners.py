import subprocess
import unittest
from pathlib import Path


RUNNERS_DIR = Path(__file__).resolve().parents[1]
LEGACY_DIR = RUNNERS_DIR / "legacy"


class PostgreSQLShellRunnerTest(unittest.TestCase):
    def test_readable_entry_points_publish_expected_inventories(self):
        expected = {
            "run_main_three_rounds.sh": "suite=main runs=3 queries=96",
            "run_pure_join_three_rounds.sh": "suite=pure_join runs=3 queries=96",
            "run_update_three_rounds.sh": "suite=update runs=3 queries=12",
            "run_update_single_round.sh": "suite=update runs=1 queries=12",
        }
        for filename, summary in expected.items():
            with self.subTest(filename=filename):
                completed = subprocess.run(
                    ["bash", str(LEGACY_DIR / filename), "--list"],
                    text=True,
                    capture_output=True,
                    check=True,
                )
                lines = completed.stdout.splitlines()
                self.assertEqual(lines[0], summary)
                self.assertEqual(len(lines) - 1, int(summary.rsplit("=", 1)[1]))

    def test_common_implementation_is_source_only(self):
        completed = subprocess.run(
            ["bash", str(LEGACY_DIR / "postgresql_benchmark_common.sh")],
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("source this file", completed.stderr)

    def test_update_restore_paths_are_rendered_without_host_identity(self):
        command = r'''
set -uo pipefail
SUITE_NAME=test RUNS=1 DEFAULT_RESULT_FILE=.local/test.csv REQUIRE_AGE=1 UPDATE_MODE=1
source "$1"
GRBENCH_POSTGRES_UPDATE_PREPARED_ROOT=/srv/grbench/update
load_sql_file "$2"
[[ "$LOADED_SQL" == *"/srv/grbench/update/grbench_update1_papers_id_masked.csv"* ]]
[[ "$LOADED_SQL" != *"/home/"* ]]
'''
        subprocess.run(
            [
                "bash",
                "-c",
                command,
                "runner-test",
                str(LEGACY_DIR / "postgresql_benchmark_common.sh"),
                str(RUNNERS_DIR.parent / "queries" / "Update" / "1b.sql"),
            ],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
