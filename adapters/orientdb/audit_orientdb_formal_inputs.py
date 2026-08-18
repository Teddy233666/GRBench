#!/usr/bin/env python3
"""Audit formal OrientDB benchmark inputs without opening any database."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

import audit_benchmark_contract
import run_orientdb


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
DEFAULT_QUERY_ROOT = ROOT / "queries"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "benchmark" / "queries" / "canonical"
DEFAULT_ORACLE = Path(
    os.environ.get("GRBENCH_ORIENTDB_ORACLE", REPO_ROOT / ".local" / "orientdb-oracle.json")
)
REUSED_SFS = ["sf10_0", "sf10_1", "sf10_2"]
EXPECTED_REUSED_TIMEOUTS = {
    ("sf10_2", "update/Update/1a.sql"),
    ("sf10_2", "update/Update/3a.sql"),
}


def oracle_error_count(oracle: Dict[str, object], scale_factors: Sequence[str]) -> int:
    errors = oracle.get("errors", {})
    if not isinstance(errors, dict):
        return 1
    total = 0
    for sf in scale_factors:
        sf_errors = errors.get(sf, {})
        if not isinstance(sf_errors, dict):
            total += 1
        else:
            total += len(sf_errors)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERY_ROOT)
    parser.add_argument("--source-query-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument(
        "--reuse-update-results",
        action="append",
        type=Path,
        default=None,
        help="Contract-v4 Update result directory or CSV. Repeatable.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    reuse_sources = args.reuse_update_results or []
    if not reuse_sources:
        raise SystemExit(
            "at least one --reuse-update-results path is required; historical readiness "
            "artifacts are not distributed"
        )
    failures: List[str] = []
    static_failures = audit_benchmark_contract.audit(
        args.source_query_root,
        args.query_root,
    )
    failures.extend(f"static:{problem}" for problem in static_failures)

    queries = run_orientdb.discover_queries(args.query_root)
    read_queries = [query for query in queries if query.category != "update"]
    update_queries = [query for query in queries if query.category == "update"]
    if len(read_queries) != 111:
        failures.append(f"read_query_count={len(read_queries)},required=111")
    if len(update_queries) != 12:
        failures.append(f"update_query_count={len(update_queries)},required=12")

    oracle = run_orientdb.load_expected_results(str(args.oracle))
    oracle_validation = run_orientdb.validate_expected_results(
        oracle,
        queries,
        args.source_query_root,
        run_orientdb.SCALE_FACTORS,
    )
    if oracle_validation.get("status") != "PASS":
        failures.extend(
            f"oracle:{problem}"
            for problem in oracle_validation.get("problems", [])
        )
    oracle_errors = oracle_error_count(oracle, run_orientdb.SCALE_FACTORS)
    if oracle_errors:
        failures.append(f"oracle_error_count={oracle_errors},required=0")

    try:
        reused, provenance = run_orientdb.load_reused_update_results(
            [str(path) for path in reuse_sources],
            REUSED_SFS,
            update_queries,
            args.source_query_root,
            required_runs=1,
            required_warmup_runs=0,
            required_resource_sample_interval=0.01,
        )
    except SystemExit as exc:
        failures.append(f"reused_updates:{exc}")
        reused = {}
        provenance = []

    expected_pairs = {
        (sf, query.rel_path)
        for sf in REUSED_SFS
        for query in update_queries
    }
    missing_pairs = sorted(expected_pairs - set(reused))
    extra_pairs = sorted(set(reused) - expected_pairs)
    failures.extend(f"missing_reused_update:{sf}:{path}" for sf, path in missing_pairs)
    failures.extend(f"extra_reused_update:{sf}:{path}" for sf, path in extra_pairs)

    observed_timeouts = {
        key for key, row in reused.items() if row.get("status") == "TIMEOUT"
    }
    if observed_timeouts != EXPECTED_REUSED_TIMEOUTS:
        failures.append(
            "reused_timeout_set_mismatch:"
            f"actual={sorted(observed_timeouts)},required={sorted(EXPECTED_REUSED_TIMEOUTS)}"
        )

    status_counts = Counter(str(row.get("status", "")) for row in reused.values())
    per_sf_counts = Counter(sf for sf, _path in reused)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL" if failures else "PASS",
        "database_access": "NONE",
        "benchmark_contract_version": run_orientdb.BENCHMARK_CONTRACT_VERSION,
        "query_root": str(args.query_root.resolve()),
        "source_query_root": str(args.source_query_root.resolve()),
        "query_counts": {
            "all": len(queries),
            "reads": len(read_queries),
            "updates": len(update_queries),
        },
        "static_audit": {
            "status": "FAIL" if static_failures else "PASS",
            "problems": static_failures,
        },
        "oracle": {
            "path": str(args.oracle.resolve()),
            "status": oracle_validation.get("status"),
            "query_count_per_sf": len(read_queries),
            "scale_factors": run_orientdb.SCALE_FACTORS,
            "error_count": oracle_errors,
            "problems": oracle_validation.get("problems", []),
        },
        "reused_updates": {
            "scale_factors": REUSED_SFS,
            "row_count": len(reused),
            "per_sf_counts": dict(sorted(per_sf_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "expected_timeouts": [
                {"sf": sf, "sql_file": path}
                for sf, path in sorted(EXPECTED_REUSED_TIMEOUTS)
            ],
            "measurement_contract": {
                "runs": 1,
                "warmup_runs": 0,
                "resource_sampling_interval_seconds": 0.01,
                "update_batch_size": run_orientdb.DEFAULT_UPDATE_BATCH_SIZE,
            },
            "provenance": provenance,
        },
        "post_sf10_3_phase_expected_rows": {
            "reads_sf10_0_to_sf10_3": 4 * len(read_queries),
            "updates_sf10_0_to_sf10_3": 4 * len(update_queries),
            "reused_updates_sf10_0_to_sf10_2": len(expected_pairs),
            "fresh_updates_sf10_3": len(update_queries),
        },
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        print(f"FAIL: {len(failures)} formal input problem(s); report={args.output}")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "PASS: 111 unique reads/SF, 12 Updates/SF, five-SF oracle, and "
        f"{len(reused)} reusable Update rows; report={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
