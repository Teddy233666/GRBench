#!/usr/bin/env python3
"""Validate that processed SF directories contain the canonical 30 CSV files."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "data" / "schema" / "sciscinet.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / "data" / "processed")),
    )
    parser.add_argument("--sf", action="append", choices=[f"sf10_{i}" for i in range(5)])
    return parser.parse_args()


def expected_files() -> list[str]:
    spec = importlib.util.spec_from_file_location("grbench_sciscinet_schema", SCHEMA)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load schema contract: {SCHEMA}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = module.source_csvs()
    if len(files) != 30:
        raise RuntimeError(f"schema contract must define 30 unique CSV files, found {len(files)}")
    return files


def main() -> int:
    args = parse_args()
    required = expected_files()
    failures = 0
    for sf in args.sf or [f"sf10_{i}" for i in range(5)]:
        root = args.data_root / sf
        missing = [name for name in required if not (root / name).is_file()]
        print(f"{sf}: present={len(required) - len(missing)} required={len(required)}")
        for name in missing:
            print(f"  MISSING {name}")
        failures += len(missing)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
