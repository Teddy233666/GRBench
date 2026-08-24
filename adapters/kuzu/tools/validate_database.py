#!/usr/bin/env python3
"""Smoke-check a Kuzu database or apply a published exact-count profile."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import kuzu


ADAPTER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ADAPTER_DIR.parents[1]
DEFAULT_DB = REPO_ROOT / ".local" / "kuzu" / "db" / "db_sf10_4"

REQUIRED_NODES = (
    "Papers",
    "Authors_Gender",
    "Affiliations",
    "Fields",
    "Twitter_Metadata",
)
REQUIRED_RELATIONS = (
    "PaperReferences",
    "Papers_to_Authors",
    "contributed_from",
    "affiliated_with",
    "PaperFields",
)
SF10_4_NODES = {
    "Papers": 249_802_175,
    "Authors_Gender": 100_418_971,
    "Affiliations": 110_553,
    "Fields": 303,
    "Twitter_Metadata": 53_053_505,
}
SF10_4_RELATIONS = {
    # The raw projection has 2,494,545,461 records. Kuzu cannot create the
    # 6,951 edges whose source or target Paper is absent from the node set.
    "PaperReferences": 2_494_538_510,
    "Papers_to_Authors": 772_984_433,
    "contributed_from": 460_751_741,
    "affiliated_with": 460_751_741,
    "PaperFields": 2_543_782_314,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--count-profile",
        choices=("none", "sf10_4"),
        default="none",
        help="Use exact published counts; none only requires non-empty tables.",
    )
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--buffer-pool-gib", type=float, default=1.0)
    return parser.parse_args()


def scalar(conn: kuzu.Connection, query: str) -> int:
    result = conn.execute(query)
    return int(result.get_next()[0]) if result.has_next() else 0


def main() -> None:
    args = parse_args()
    if not args.db_path.exists():
        raise SystemExit(f"database not found: {args.db_path}")
    started = time.time()
    db = kuzu.Database(
        str(args.db_path),
        read_only=True,
        buffer_pool_size=int(args.buffer_pool_gib * 1024**3),
        max_num_threads=args.threads,
    )
    conn = kuzu.Connection(db, num_threads=args.threads)
    node_counts = SF10_4_NODES if args.count_profile == "sf10_4" else {}
    relation_counts = SF10_4_RELATIONS if args.count_profile == "sf10_4" else {}
    failures: list[str] = []
    print("kind,table,count,expected,status", flush=True)
    for table in REQUIRED_NODES:
        count = scalar(conn, f"MATCH (n:{table}) RETURN count(*);")
        expected = node_counts.get(table)
        status = "OK" if (count == expected if expected is not None else count > 0) else "MISMATCH"
        expected_label = expected if expected is not None else ">0"
        print(f"NODE,{table},{count},{expected_label},{status}", flush=True)
        if status != "OK":
            failures.append(f"{table}={count}, expected {expected_label}")
    for table in REQUIRED_RELATIONS:
        count = scalar(conn, f"MATCH ()-[r:{table}]->() RETURN count(*);")
        expected = relation_counts.get(table)
        status = "OK" if (count == expected if expected is not None else count > 0) else "MISMATCH"
        expected_label = expected if expected is not None else ">0"
        print(f"REL,{table},{count},{expected_label},{status}", flush=True)
        if status != "OK":
            failures.append(f"{table}={count}, expected {expected_label}")
    print(f"validation_seconds={time.time() - started:.3f}", flush=True)
    if failures:
        raise SystemExit("Kuzu database validation failed: " + "; ".join(failures))
    print("Kuzu database validation passed", flush=True)


if __name__ == "__main__":
    main()
