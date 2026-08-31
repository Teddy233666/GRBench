import tempfile
import unittest
from pathlib import Path
import sys

RUNNERS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNNERS_DIR))
from measurement import ensure_csv_schema, run_repeated, select_median_elapsed_run


class MeasurementContractTest(unittest.TestCase):
    def test_selects_whole_median_elapsed_run(self):
        runs = [
            {"status": "OK", "elapsed_s": 3.0, "cpu_peak_pct": 30, "rows": 1, "result": "x"},
            {"status": "OK", "elapsed_s": 1.0, "cpu_peak_pct": 10, "rows": 1, "result": "x"},
            {"status": "OK", "elapsed_s": 2.0, "cpu_peak_pct": 20, "rows": 1, "result": "x"},
        ]
        selected = select_median_elapsed_run(
            runs, warmups_requested=1, warmups_completed=1, repeats_requested=3
        )
        self.assertEqual(selected["elapsed_s"], 2.0)
        self.assertEqual(selected["cpu_peak_pct"], 20)
        self.assertEqual(selected["selected_measured_run"], 3)

    def test_runs_one_warmup_and_three_measurements(self):
        calls = []

        def run_once():
            calls.append(len(calls))
            return {"status": "OK", "elapsed_s": float(len(calls)), "rows": 1, "result": "x"}

        selected = run_repeated(run_once)
        self.assertEqual(len(calls), 4)
        self.assertEqual(selected["warmup_runs_completed"], 1)
        self.assertEqual(selected["measured_runs_completed"], 3)

    def test_marks_inconsistent_results(self):
        runs = [
            {"status": "OK", "elapsed_s": 1.0, "rows": 1, "result": "a"},
            {"status": "OK", "elapsed_s": 2.0, "rows": 1, "result": "b"},
            {"status": "OK", "elapsed_s": 3.0, "rows": 1, "result": "a"},
        ]
        selected = select_median_elapsed_run(
            runs, warmups_requested=1, warmups_completed=1, repeats_requested=3
        )
        self.assertEqual(selected["status"], "REPEAT_MISMATCH")
        self.assertEqual(selected["repeat_consistent"], "false")

    def test_preserves_terminal_status_for_partial_runs(self):
        runs = [
            {"status": "OK", "elapsed_s": 1.0, "rows": 1, "result": "a"},
            {"status": "TIMEOUT", "elapsed_s": 10.0, "rows": 0, "result": "", "error": "limit"},
        ]
        selected = select_median_elapsed_run(
            runs, warmups_requested=1, warmups_completed=1, repeats_requested=3
        )
        self.assertEqual(selected["status"], "TIMEOUT")
        self.assertEqual(selected["error"], "limit")
        self.assertEqual(selected["selected_measured_run"], 2)
        self.assertEqual(selected["elapsed_s"], 10.0)
        self.assertEqual(selected["repeat_consistent"], "false")

    def test_rejects_incompatible_existing_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            path.write_text("old,column\n1,2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                ensure_csv_schema(path, ["new", "columns"])


if __name__ == "__main__":
    unittest.main()
