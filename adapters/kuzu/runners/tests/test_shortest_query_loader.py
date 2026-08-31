import sys
import unittest
from pathlib import Path


RUNNERS_DIR = Path(__file__).resolve().parents[1]
ADAPTER_DIR = RUNNERS_DIR.parent
QUERY_ROOT = ADAPTER_DIR / "queries" / "Shortest_Path_Queries"
sys.path.insert(0, str(RUNNERS_DIR))

from shortest_query_loader import load_shortest_queries


class ShortestQueryLoaderTest(unittest.TestCase):
    def test_loads_all_queries_in_benchmark_order(self):
        queries = load_shortest_queries(QUERY_ROOT, max_unbounded_depth=8)

        self.assertEqual(
            [query["sql_file"] for query in queries],
            [f"{number}{suffix}.sql" for number in range(1, 6) for suffix in "abc"],
        )
        self.assertEqual(
            [len(query["steps"]) for query in queries],
            [8] * 3 + [3] * 3 + [4] * 3 + [9] * 3 + [2] * 3,
        )

    def test_renders_historical_exact_depth_patterns(self):
        by_name = {
            query["sql_file"]: query
            for query in load_shortest_queries(QUERY_ROOT, max_unbounded_depth=3)
        }

        self.assertIn("[:affl_assoc_affl]->", by_name["1a.sql"]["steps"][0])
        self.assertIn("[:affl_assoc_affl*2..2]->", by_name["1a.sql"]["steps"][1])
        self.assertNotIn("{{DEPTH_RANGE}}", "\n".join(by_name["1a.sql"]["steps"]))
        self.assertTrue(by_name["4a.sql"]["steps"][0].startswith("MATCH (inst_for:Affiliations)"))
        self.assertIn("[:affl_assoc_affl]->", by_name["4a.sql"]["steps"][1])
        self.assertTrue(by_name["5a.sql"]["steps"][0].startswith("MATCH (paper:Papers)"))
        self.assertIn("[:PaperReferences]->", by_name["5a.sql"]["steps"][1])

    def test_rejects_invalid_unbounded_depth(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            load_shortest_queries(QUERY_ROOT, max_unbounded_depth=0)


if __name__ == "__main__":
    unittest.main()
