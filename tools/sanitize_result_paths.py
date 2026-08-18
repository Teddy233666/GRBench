#!/usr/bin/env python3
"""Normalize workstation paths in result CSVs without changing metric cells."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "latest-observed"
HOST_PATH = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?:/home/[A-Za-z0-9_.-]+|/(?:data[23]?|workspace|root|mnt|ssd))(?:/|$)"
)
REPLACEMENTS = (
    (
        re.compile(r"/home/[^/]+/GRBench/tasks/arangodb_task/agensgraph_task/"),
        "legacy_core/tasks/arangodb_task/agensgraph_task/",
    ),
    (
        re.compile(r"/home/[^/]+/GRBench/tasks/graindb_task_copy/"),
        "legacy_core/tasks/graindb_task_copy/",
    ),
    (
        re.compile(r"/home/[^/]+/GRBench/tasks/postgresql_task/"),
        "legacy_core/tasks/postgresql_task/",
    ),
    (
        re.compile(r"/home/[^/]+/GRBench/tasks/sciscinet_tasks/Shortest_Path_Queries/"),
        "benchmark/queries/canonical/Shortest_Path_Queries/",
    ),
    (
        re.compile(r"/home/[^/]+/GRBench/tasks/sciscinet_tasks/update/Update/"),
        "benchmark/queries/canonical/update/Update/",
    ),
    (
        re.compile(r"/home/[^/]+/GRBench/tasks/sciscinet_tasks/update/"),
        "benchmark/queries/canonical/update/",
    ),
    (
        re.compile(r"/home/[^/]+/Dockerdata/kuzu_poc/queries_cypher/"),
        "adapters/kuzu/queries/",
    ),
    (
        re.compile(r"/home/[^/]+/Dockerdata/kuzu_poc/update_work_warm_rss/"),
        ".local/kuzu-update-work/",
    ),
    (
        re.compile(r"/home/[^/]+/Dockerdata/kuzu_poc/db/"),
        ".local/kuzu-databases/",
    ),
    (re.compile(r"/data/task/"), "legacy_core/tasks/agensgraph_task/"),
    (
        re.compile(r"/workspace/task/"),
        "legacy_core/tasks/sciscinet_tasks/",
    ),
)


def normalized(cell: str) -> tuple[str, int]:
    replacements = 0
    for pattern, alias in REPLACEMENTS:
        cell, count = pattern.subn(alias, cell)
        if count:
            replacements += count
    return cell, replacements


def process(path: Path, write: bool) -> tuple[int, list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    changed = 0
    unresolved: list[str] = []
    output: list[list[str]] = []
    for row_number, row in enumerate(rows, start=1):
        normalized_row = []
        for cell in row:
            value, count = normalized(cell)
            changed += count
            if HOST_PATH.search(value):
                unresolved.append(f"{path.relative_to(ROOT)}:{row_number}")
            normalized_row.append(value)
        output.append(normalized_row)

    if changed and write and not unresolved:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle, lineterminator="\n").writerows(output)
        temporary.replace(path)
    return changed, unresolved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite CSVs using stable path aliases",
    )
    args = parser.parse_args()

    total = 0
    errors: list[str] = []
    for path in sorted(RESULTS.rglob("*.csv")):
        changed, unresolved = process(path, args.write)
        total += changed
        errors.extend(unresolved)

    if errors:
        print("Unrecognized absolute host paths remain:")
        for location in sorted(set(errors)):
            print(f"  {location}")
        return 1
    if total and not args.write:
        print(f"Found {total} host path value(s); run again with --write.")
        return 1
    action = "normalized" if args.write else "verified"
    print(f"Published result paths {action}; replacements: {total}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
