#!/usr/bin/env python3
"""Recover an interrupted native OrientDB Update to a verified baseline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Sequence

import run_orientdb


def integer_mapping(value: object, label: str) -> Dict[str, int]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} is missing or is not an object")
    try:
        return {str(key): int(count) for key, count in value.items()}
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{label} contains a non-integer count: {exc}") from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", required=True, choices=run_orientdb.SCALE_FACTORS)
    parser.add_argument("--update-file", required=True)
    parser.add_argument("--baseline-preflight", required=True, type=Path)
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / ".local" / "orientdb" / "databases",
    )
    parser.add_argument(
        "--orientdb-home",
        type=Path,
        default=run_orientdb.DEFAULT_ORIENTDB_HOME,
    )
    parser.add_argument(
        "--java-home",
        type=Path,
        default=run_orientdb.DEFAULT_JAVA_HOME,
    )
    parser.add_argument("--heap", default="-Xms4g -Xmx64g")
    parser.add_argument("--timeout", type=int, default=run_orientdb.QUERY_TIMEOUT_S)
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=run_orientdb.DEFAULT_UPDATE_RECOVERY_MAX_ATTEMPTS,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=run_orientdb.DEFAULT_UPDATE_BATCH_SIZE,
    )
    parser.add_argument("--log-file", required=True, type=Path)
    parser.add_argument("--session-log", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    filename = Path(args.update_file).name
    if filename not in run_orientdb.UPDATE_BATCH_OPERATIONS:
        raise SystemExit(f"unsupported native Update file: {filename}")
    if args.timeout <= 0 or args.max_attempts < 1 or args.batch_size < 1:
        raise SystemExit("timeout, max-attempts, and batch-size must be positive")

    preflight = json.loads(args.baseline_preflight.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise SystemExit("baseline preflight did not pass")
    if preflight.get("sf") != args.sf:
        raise SystemExit(
            f"baseline preflight SF mismatch: expected={args.sf},actual={preflight.get('sf')}"
        )

    database_counts = integer_mapping(preflight.get("database_counts"), "database_counts")
    support_counts = integer_mapping(
        preflight.get("update_support_counts"),
        "update_support_counts",
    )
    affected_classes = run_orientdb.UPDATE_AFFECTED_CLASSES[filename]
    staging_classes = sorted(set(run_orientdb.UPDATE_CLASS_STAGING[filename].values()))
    support_classes = run_orientdb.UPDATE_SUPPORT_CLASSES[filename]
    required_classes = set(affected_classes) | set(staging_classes) | set(support_classes)
    missing_classes = sorted(required_classes - set(database_counts) - set(support_counts))
    if missing_classes:
        raise SystemExit("baseline preflight is missing classes: " + ",".join(missing_classes))

    baseline_counts = {name: database_counts[name] for name in affected_classes}
    staging_counts = {name: database_counts[name] for name in staging_classes}
    baseline_support_counts = {name: support_counts[name] for name in support_classes}
    if any(count != 0 for count in baseline_support_counts.values()):
        raise SystemExit(
            "baseline preflight support classes were not empty: "
            + json.dumps(baseline_support_counts, sort_keys=True)
        )

    recovery_context = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sf": args.sf,
        "update_file": filename,
        "baseline_preflight": str(args.baseline_preflight),
        "database": str(args.db_dir / args.sf),
        "heap": args.heap,
        "timeout_seconds": args.timeout,
        "max_attempts": args.max_attempts,
        "batch_size": args.batch_size,
        "baseline_counts": baseline_counts,
        "baseline_support_counts": baseline_support_counts,
        "staging_counts": staging_counts,
    }
    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    args.session_log.parent.mkdir(parents=True, exist_ok=True)
    args.log_file.write_text(
        json.dumps(recovery_context, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    session = run_orientdb.OrientDBConsoleSession(
        db_path=args.db_dir / args.sf,
        orientdb_home=args.orientdb_home,
        java_home=args.java_home,
        heap=args.heap,
        sample_interval_s=run_orientdb.DEFAULT_RESOURCE_SAMPLE_INTERVAL_S,
        session_log_path=args.session_log,
    )
    try:
        session.start()
        restored, note, output = run_orientdb.recover_and_verify_update_baseline(
            session=session,
            filename=filename,
            batch_size=args.batch_size,
            baseline_counts=baseline_counts,
            baseline_support_counts=baseline_support_counts,
            staging_counts=staging_counts,
            timeout_s=args.timeout,
            process_lost=False,
            max_attempts=args.max_attempts,
        )
    finally:
        session.close()

    completion = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "restored": restored,
        "note": note,
    }
    with args.log_file.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(output)
        if output and not output.endswith("\n"):
            handle.write("\n")
        handle.write(json.dumps(completion, indent=2, sort_keys=True) + "\n")
    print(f"RECOVERY_{'PASS' if restored else 'FAIL'} {note}", flush=True)
    return 0 if restored else 2


if __name__ == "__main__":
    raise SystemExit(main())
