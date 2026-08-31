#!/usr/bin/env python3
"""Repair skipped OrientDB edge rows with _MissingEndpoint placeholders."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Sequence

TOOL_DIR = Path(__file__).resolve().parent
LOADERS_DIR = TOOL_DIR.parent
ADAPTER_DIR = LOADERS_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
sys.path.insert(0, str(ADAPTER_DIR / "runners"))
from run_orientdb import (
    DEFAULT_CONSOLE_HEAP,
    DEFAULT_JAVA_HOME,
    DEFAULT_ORIENTDB_HOME,
    SCALE_FACTORS,
    query_load_manifest,
)


ROOT = ADAPTER_DIR
DEFAULT_DB_ROOT = REPO_ROOT / ".local" / "orientdb" / "databases"
DEFAULT_DATA_ROOT = REPO_ROOT / "data" / "processed"
DEFAULT_QUERY_ROOT = ADAPTER_DIR / "queries"
DEFAULT_UPDATE_DIR = REPO_ROOT / ".local" / "update-staging"
TABLE_CONFIG = REPO_ROOT / ".local" / "orientdb" / "build" / "loader" / "config" / "tables.tsv"


def edge_classes() -> set[str]:
    with TABLE_CONFIG.open(newline="") as handle:
        return {row["name"] for row in csv.DictReader(handle, delimiter="\t") if row["kind"] == "E"}


def incomplete_edges(rows: Sequence[Dict[str, object]], configured_edges: set[str]) -> List[Dict[str, object]]:
    incomplete = []
    for row in rows:
        class_name = str(row.get("class_name", ""))
        if class_name not in configured_edges:
            continue
        try:
            source_rows = int(str(row.get("source_rows", "0") or "0"))
            loaded_rows = int(str(row.get("loaded_rows", "0") or "0"))
            skipped_rows = int(str(row.get("skipped_rows", "0") or "0"))
        except ValueError:
            continue
        if (
            source_rows != loaded_rows
            or skipped_rows != 0
            or str(row.get("source_rows_verified", "")).lower() not in {"true", "1"}
        ):
            incomplete.append({**row, "missing_rows": source_rows - loaded_rows})
    return incomplete


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", action="append", choices=SCALE_FACTORS)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_ROOT)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERY_ROOT)
    parser.add_argument("--update-dir", type=Path, default=DEFAULT_UPDATE_DIR)
    parser.add_argument("--orientdb-home", type=Path, default=DEFAULT_ORIENTDB_HOME)
    parser.add_argument("--java-home", type=Path, default=DEFAULT_JAVA_HOME)
    parser.add_argument("--heap", default="32g")
    parser.add_argument("--direct-memory", default="80g")
    parser.add_argument("--disk-cache-mb", type=int, default=65536)
    parser.add_argument("--batch-size", type=int, default=50000)
    parser.add_argument("--console-heap", default=DEFAULT_CONSOLE_HEAP)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configured_edges = edge_classes()
    selected_sfs = args.sf or SCALE_FACTORS
    repair_sfs = []
    for sf in selected_sfs:
        rows = query_load_manifest(
            sf,
            args.db_dir,
            args.orientdb_home,
            args.java_home,
            args.console_heap,
            REPO_ROOT / ".local" / "logs" / "orientdb" / "orphan-edge-repair" / sf / "manifest_worker.log",
        )
        candidates = incomplete_edges(rows, configured_edges)
        print(f"[{sf}] incomplete edge classes={len(candidates)}")
        for row in candidates:
            print(
                f"  {row['class_name']}: source={row['source_rows']} "
                f"loaded={row['loaded_rows']} missing={row['missing_rows']}"
            )
        if candidates:
            repair_sfs.append(sf)

    if not args.execute:
        print("Dry run only. Pass --execute to reload listed edge classes with placeholder endpoints.")
        return 0

    for sf in repair_sfs:
        command = [
            sys.executable,
            str(LOADERS_DIR / "load_orientdb_data.py"),
            "--sf",
            sf,
            "--db-dir",
            str(args.db_dir),
            "--data-root",
            str(args.data_root),
            "--query-root",
            str(args.query_root),
            "--update-dir",
            str(args.update_dir),
            "--orientdb-home",
            str(args.orientdb_home),
            "--java-home",
            str(args.java_home),
            "--heap",
            args.heap,
            "--direct-memory",
            args.direct_memory,
            "--disk-cache-mb",
            str(args.disk_cache_mb),
            "--batch-size",
            str(args.batch_size),
            "--orphan-edge-mode",
            "placeholder",
            "--resume",
            "--repair-skipped-edges",
            "--skip-updates",
            "--skip-final-counts",
        ]
        print(f"[{sf}] starting placeholder edge repair", flush=True)
        subprocess.run(command, check=True, cwd=str(ROOT))
    if repair_sfs:
        command = [
            sys.executable,
            str(LOADERS_DIR / "load_orientdb_data.py"),
            "--db-dir",
            str(args.db_dir),
            "--data-root",
            str(args.data_root),
            "--query-root",
            str(args.query_root),
            "--update-dir",
            str(args.update_dir),
            "--orientdb-home",
            str(args.orientdb_home),
            "--java-home",
            str(args.java_home),
            "--heap",
            args.heap,
            "--direct-memory",
            args.direct_memory,
            "--disk-cache-mb",
            str(args.disk_cache_mb),
            "--batch-size",
            str(args.batch_size),
            "--update-source-mode",
            "derived",
            "--derive-updates-only",
            "--skip-final-counts",
        ]
        for sf in repair_sfs:
            command.extend(["--sf", sf])
        print(f"deriving per-SF Update snapshots for {', '.join(repair_sfs)}", flush=True)
        subprocess.run(command, check=True, cwd=str(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
