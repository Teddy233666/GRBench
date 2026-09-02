#!/usr/bin/env python3
"""Unified PostgreSQL/Apache AGE loader for the GRBench SciSciNet profile."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

from loader_core import (
    DATA_PROFILE,
    REPO_ROOT,
    LoadStep,
    TableSpec,
    audit_source_files,
    build_load_steps,
    canonical_tables,
    quoted_identifier,
    render_plan,
    safe_identifier,
)
from prepare_age import prepare_age_dataset


DEFAULT_DATA_ROOT = Path(os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / "data" / "processed"))
DEFAULT_PREPARED_ROOT = Path(
    os.environ.get("GRBENCH_POSTGRES_PREPARED_ROOT", REPO_ROOT / ".local" / "prepared")
)
DEFAULT_STATE_ROOT = REPO_ROOT / ".local" / "postgresql"
SCALE_FACTORS = [f"sf10_{index}" for index in range(5)]


def _add_dataset_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sf", choices=SCALE_FACTORS, required=True)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--prepared-root", type=Path, default=DEFAULT_PREPARED_ROOT)
    parser.add_argument("--only-table", action="append", default=[])


def _add_projection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--projection", choices=["relational", "age"], required=True)
    parser.add_argument("--graph-name", default="sciscinet_graph")
    parser.add_argument(
        "--server-prepared-root",
        type=Path,
        default=None,
        help="Prepared-root path visible to the PostgreSQL server; defaults to --prepared-root.",
    )


def _add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--psql", default="psql")
    parser.add_argument("--host", default=os.environ.get("POSTGRES_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("POSTGRES_PORT", "5432")))
    parser.add_argument("--database", default=os.environ.get("POSTGRES_DATABASE", "grbench"))
    parser.add_argument("--username", default=os.environ.get("POSTGRES_USERNAME", "grbench"))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Render the complete SQL load plan without opening PostgreSQL.")
    _add_dataset_arguments(plan)
    _add_projection_arguments(plan)
    plan.add_argument("--rebuild", action="store_true")
    plan.add_argument("--output", type=Path, default=None)

    prepare = subparsers.add_parser("prepare-age", help="Prepare AGE vertex/edge CSVs and endpoint maps.")
    _add_dataset_arguments(prepare)
    prepare.add_argument("--batch-size", type=int, default=1_000_000)
    prepare.add_argument("--orphan-edge-mode", choices=["fail", "skip"], default="fail")
    mode = prepare.add_mutually_exclusive_group()
    mode.add_argument("--overwrite", action="store_true")
    mode.add_argument("--resume", action="store_true")

    load = subparsers.add_parser("load", help="Execute a relational or AGE load with persistent step state.")
    _add_dataset_arguments(load)
    _add_projection_arguments(load)
    _add_connection_arguments(load)
    load_mode = load.add_mutually_exclusive_group()
    load_mode.add_argument("--rebuild", action="store_true")
    load_mode.add_argument("--resume", action="store_true")
    load.add_argument("--source-scan", choices=["headers", "full"], default="full")
    load.add_argument("--skip-final-counts", action="store_true")
    load.add_argument("--dry-run", action="store_true")
    load.add_argument("--plan-output", type=Path, default=None)
    load.add_argument("--manifest", type=Path, default=None)

    validate = subparsers.add_parser("validate", help="Validate source files and optionally loaded row counts.")
    _add_dataset_arguments(validate)
    _add_projection_arguments(validate)
    _add_connection_arguments(validate)
    validate.add_argument("--source-scan", choices=["headers", "full"], default="full")
    validate.add_argument("--database-counts", action="store_true")
    validate.add_argument("--manifest", type=Path, default=None)

    args = parser.parse_args(argv)
    if getattr(args, "batch_size", 1) < 1:
        parser.error("--batch-size must be at least 1")
    if hasattr(args, "graph_name"):
        safe_identifier(args.graph_name)
    return args


def _selected_tables(names: Iterable[str]) -> list[TableSpec]:
    tables = canonical_tables()
    selected = {name.lower() for name in names}
    unknown = selected - {table.name.lower() for table in tables}
    if unknown:
        raise ValueError(f"unknown table(s): {', '.join(sorted(unknown))}")
    return [table for table in tables if not selected or table.name.lower() in selected]


def _selected_steps(steps: Sequence[LoadStep], names: Iterable[str]) -> list[LoadStep]:
    selected = {name.lower() for name in names}
    if not selected:
        return list(steps)
    output = [step for step in steps if step.table.lower() in selected]
    if any(step.kind in {"vertex", "edge"} for step in output):
        output = [step for step in steps if step.kind == "graph"] + output
    return output


def _server_prepared_root(args: argparse.Namespace) -> Path:
    if args.server_prepared_root is None:
        return args.prepared_root.resolve()
    if not args.server_prepared_root.is_absolute():
        raise ValueError("--server-prepared-root must be an absolute path visible to PostgreSQL")
    return args.server_prepared_root


def build_steps(args: argparse.Namespace) -> list[LoadStep]:
    return _selected_steps(
        build_load_steps(
            args.projection,
            args.sf,
            args.data_root.resolve(),
            args.prepared_root.resolve(),
            _server_prepared_root(args),
            args.graph_name,
            bool(getattr(args, "rebuild", False)),
        ),
        args.only_table,
    )


def default_plan_path(args: argparse.Namespace) -> Path:
    suffix = _partial_suffix(args.only_table)
    return DEFAULT_STATE_ROOT / args.sf / args.projection / f"load_plan{suffix}.sql"


def default_manifest_path(args: argparse.Namespace) -> Path:
    suffix = _partial_suffix(args.only_table)
    return DEFAULT_STATE_ROOT / args.sf / args.projection / f"load_manifest{suffix}.json"


def _partial_suffix(names: Iterable[str]) -> str:
    selected = sorted(name.lower() for name in names)
    if not selected:
        return ""
    readable = "_".join(selected)
    if len(readable) > 40:
        readable = hashlib.sha256("\0".join(selected).encode()).hexdigest()[:16]
    return f".partial_{readable}"


def write_plan(args: argparse.Namespace, steps: Sequence[LoadStep]) -> Path:
    output = getattr(args, "output", None) or getattr(args, "plan_output", None) or default_plan_path(args)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_plan(steps), encoding="utf-8")
    return output


def _psql_command(args: argparse.Namespace, *extra: str) -> list[str]:
    return [
        args.psql,
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.username,
        "-d",
        args.database,
        *extra,
    ]


def _psql_environment() -> dict[str, str]:
    environment = os.environ.copy()
    password = environment.get("POSTGRES_PASSWORD", "")
    if password:
        environment["PGPASSWORD"] = password
    environment.setdefault("LC_ALL", "C.UTF-8")
    return environment


def execute_sql(args: argparse.Namespace, sql: str) -> str:
    completed = subprocess.run(
        _psql_command(args),
        input=sql,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=_psql_environment(),
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout[-8000:])
    return completed.stdout


def query_scalar(args: argparse.Namespace, sql: str) -> int:
    completed = subprocess.run(
        _psql_command(args, "-A", "-t", "-c", sql),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=_psql_environment(),
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout[-8000:])
    value = completed.stdout.strip().splitlines()[-1]
    return int(value)


def _configuration(args: argparse.Namespace) -> dict[str, object]:
    return {
        "profile": DATA_PROFILE,
        "sf": args.sf,
        "projection": args.projection,
        "data_root": str(args.data_root.resolve()),
        "prepared_root": str(args.prepared_root.resolve()),
        "server_prepared_root": str(_server_prepared_root(args)),
        "graph_name": args.graph_name,
        "database": args.database,
        "host": args.host,
        "port": args.port,
        "username": args.username,
        "only_tables": sorted(name.lower() for name in args.only_table),
    }


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _age_prepare_rows(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    path = args.prepared_root / f"{args.sf}_postgresql" / "age" / "prepare_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"AGE preparation manifest not found: {path}; run the prepare-age command first"
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("sf") != args.sf or manifest.get("projection") != "age":
        raise ValueError(f"AGE preparation manifest does not match {args.sf}: {path}")
    rows = {row["table"]: row for row in manifest.get("tables", []) if row.get("status") == "DONE"}
    required = {
        table.name
        for table in _selected_tables(args.only_table)
        if table.kind in {"vertex", "edge"}
    }
    missing = required - set(rows)
    if missing:
        raise ValueError(f"AGE preparation is incomplete: {', '.join(sorted(missing))}")
    return rows


def _validate_age_preparation(
    args: argparse.Namespace,
    rows: dict[str, dict[str, Any]],
    source_inventory: dict[str, dict[str, object]],
) -> None:
    by_name = {table.name: table for table in _selected_tables(args.only_table)}
    errors = []
    for name, row in rows.items():
        table = by_name.get(name)
        if table is None or table.kind not in {"vertex", "edge"}:
            continue
        output_path = Path(str(row.get("output_path", "")))
        if not output_path.is_file():
            errors.append(f"{name}: prepared CSV is missing: {output_path}")
        expected_sha = source_inventory[table.csv_name].get("sha256")
        if expected_sha is not None and row.get("source_sha256") != expected_sha:
            errors.append(f"{name}: prepared source SHA-256 differs from the current canonical CSV")
    if errors:
        raise ValueError("AGE preparation validation failed: " + "; ".join(errors))


def _source_inventory(args: argparse.Namespace) -> dict[str, dict[str, object]]:
    return audit_source_files(
        args.data_root / args.sf,
        _selected_tables(args.only_table),
        full=args.source_scan == "full",
    )


def _expected_rows(
    table: TableSpec,
    source_inventory: dict[str, dict[str, object]],
    age_rows: dict[str, dict[str, Any]],
) -> int | None:
    if table.kind in {"vertex", "edge"} and table.name in age_rows:
        return int(age_rows[table.name]["loaded_rows"])
    value = source_inventory[table.csv_name].get("source_rows")
    return int(value) if value is not None else None


def _count_sql(args: argparse.Namespace, table: TableSpec) -> str:
    if args.projection == "age" and table.kind in {"vertex", "edge"}:
        return (
            "LOAD 'age'; SET search_path = ag_catalog, \"$user\", public; "
            f"SELECT count(*) FROM {quoted_identifier(args.graph_name)}.{quoted_identifier(table.name)};"
        )
    return f"SELECT count(*) FROM {safe_identifier(table.name)};"


def validate_database_counts(
    args: argparse.Namespace,
    source_inventory: dict[str, dict[str, object]],
    age_rows: dict[str, dict[str, Any]],
) -> list[dict[str, object]]:
    results = []
    for table in _selected_tables(args.only_table):
        expected = _expected_rows(table, source_inventory, age_rows)
        actual = query_scalar(args, _count_sql(args, table))
        status = "OK" if expected is None or actual == expected else "MISMATCH"
        results.append({"table": table.name, "expected_rows": expected, "loaded_rows": actual, "status": status})
    return results


def require_valid_counts(results: Sequence[dict[str, object]]) -> None:
    errors = [
        f"{row['table']}: expected={row['expected_rows']}, loaded={row['loaded_rows']}"
        for row in results
        if row["status"] != "OK"
    ]
    if errors:
        raise RuntimeError("database row-count validation failed: " + "; ".join(errors))


def command_plan(args: argparse.Namespace) -> int:
    steps = build_steps(args)
    output = write_plan(args, steps)
    print(f"profile={DATA_PROFILE} projection={args.projection} sf={args.sf} steps={len(steps)}")
    print(output)
    return 0


def command_prepare_age(args: argparse.Namespace) -> int:
    manifest = prepare_age_dataset(
        args.sf,
        args.data_root,
        args.prepared_root,
        batch_size=args.batch_size,
        orphan_edge_mode=args.orphan_edge_mode,
        overwrite=args.overwrite,
        resume=args.resume,
        only_tables=args.only_table,
    )
    print(manifest)
    return 0


def command_load(args: argparse.Namespace) -> int:
    if args.projection == "age" and args.rebuild and args.only_table:
        raise ValueError("AGE --rebuild cannot be combined with --only-table because rebuild drops the graph")
    if not args.dry_run and not args.skip_final_counts and args.source_scan != "full":
        raise ValueError("exact final counts require --source-scan full")
    steps = build_steps(args)
    plan_path = write_plan(args, steps)
    print(f"plan={plan_path} steps={len(steps)}")
    if args.dry_run:
        return 0

    source_inventory = _source_inventory(args)
    age_rows = _age_prepare_rows(args) if args.projection == "age" else {}
    if args.projection == "age":
        _validate_age_preparation(args, age_rows, source_inventory)
    manifest_path = args.manifest or default_manifest_path(args)
    configuration = _configuration(args)
    configuration_sha256 = _fingerprint(configuration)
    previous = _load_manifest(manifest_path) if args.resume else {}
    if previous and previous.get("configuration_sha256") != configuration_sha256:
        raise ValueError("existing load manifest does not match the requested configuration")
    if previous and previous.get("source_files") != source_inventory:
        raise ValueError("canonical source files changed since the resumable load began")
    statuses = {
        row["step_id"]: row
        for row in previous.get("steps", [])
        if isinstance(row, dict)
    }
    manifest: dict[str, Any] = {
        "configuration": configuration,
        "configuration_sha256": configuration_sha256,
        "source_files": source_inventory,
        "steps": [statuses[key] for key in sorted(statuses)],
        "database_counts": previous.get("database_counts", []),
    }
    _write_manifest(manifest_path, manifest)

    for step in steps:
        existing = statuses.get(step.step_id)
        if args.resume and existing and existing.get("status") == "DONE":
            current_sql_sha256 = hashlib.sha256(step.sql.encode()).hexdigest()
            if existing.get("sql_sha256") != current_sql_sha256:
                raise ValueError(f"load SQL changed for completed step {step.step_id}")
            print(f"SKIP {step.step_id}")
            continue
        print(f"LOAD {step.step_id}", flush=True)
        status = {
            "step_id": step.step_id,
            "table": step.table,
            "kind": step.kind,
            "source_path": str(step.source_path) if step.source_path else "",
            "sql_sha256": hashlib.sha256(step.sql.encode()).hexdigest(),
            "status": "RUNNING",
        }
        statuses[step.step_id] = status
        manifest["steps"] = [statuses[key] for key in sorted(statuses)]
        _write_manifest(manifest_path, manifest)
        try:
            execute_sql(args, step.sql)
        except Exception as exc:
            status["status"] = "FAILED"
            status["error"] = str(exc)[-2000:]
            manifest["steps"] = [statuses[key] for key in sorted(statuses)]
            _write_manifest(manifest_path, manifest)
            raise
        status["status"] = "DONE"
        status.pop("error", None)
        manifest["steps"] = [statuses[key] for key in sorted(statuses)]
        _write_manifest(manifest_path, manifest)

    if not args.skip_final_counts:
        manifest["database_counts"] = validate_database_counts(args, source_inventory, age_rows)
        _write_manifest(manifest_path, manifest)
        require_valid_counts(manifest["database_counts"])
    print(manifest_path)
    return 0


def command_validate(args: argparse.Namespace) -> int:
    if args.database_counts and args.source_scan != "full":
        raise ValueError("--database-counts requires --source-scan full")
    source_inventory = _source_inventory(args)
    print(
        f"source_profile={DATA_PROFILE} sf={args.sf} files={len(source_inventory)} "
        f"mode={args.source_scan}"
    )
    if args.database_counts:
        age_rows = _age_prepare_rows(args) if args.projection == "age" else {}
        if args.projection == "age":
            _validate_age_preparation(args, age_rows, source_inventory)
        counts = validate_database_counts(args, source_inventory, age_rows)
        manifest_path = args.manifest or default_manifest_path(args)
        manifest = _load_manifest(manifest_path)
        manifest["database_counts"] = counts
        _write_manifest(manifest_path, manifest)
        require_valid_counts(counts)
        print(f"database_counts={len(counts)} manifest={manifest_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    commands = {
        "plan": command_plan,
        "prepare-age": command_prepare_age,
        "load": command_load,
        "validate": command_validate,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
