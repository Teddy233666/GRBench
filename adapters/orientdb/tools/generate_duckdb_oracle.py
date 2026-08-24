#!/usr/bin/env python3
"""Generate canonical GRBench read-result hashes from DuckDB reference data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Sequence

import duckdb

TOOL_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = TOOL_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
sys.path.insert(0, str(ADAPTER_DIR / "runners"))
from run_orientdb import CATEGORIES, canonical_scalar_text, discover_queries, query_suite_sha256


ROOT = ADAPTER_DIR
DEFAULT_QUERY_ROOT = REPO_ROOT / "benchmark" / "queries" / "canonical"
DEFAULT_DATABASE_ROOT = Path(
    os.environ.get("GRBENCH_DUCKDB_ROOT", REPO_ROOT / ".local" / "duckdb")
)
DEFAULT_DATABASES = {
    f"sf10_{index}": DEFAULT_DATABASE_ROOT / f"sciscinet_graph_{index}.duckdb"
    for index in range(5)
}
READ_CATEGORIES = [category for category in CATEGORIES if category != "update"]
ORACLE_FORMAT_VERSION = "grbench-canonical-values-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", action="append", choices=sorted(DEFAULT_DATABASES))
    parser.add_argument("--category", action="append", choices=READ_CATEGORIES)
    parser.add_argument("--match", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERY_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    return value


def canonical_rows(rows: Sequence[Sequence[object]]) -> List[List[str]]:
    normalized = [
        [canonical_scalar_text(json_value(value)) for value in row]
        for row in rows
    ]
    return sorted(normalized)


def values_digest(rows: Sequence[Sequence[object]]) -> str:
    encoded = json.dumps([canonical_rows(rows)], ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_existing(path: Path) -> Dict[str, object]:
    if not path.exists() or not path.stat().st_size:
        return {"results": {}, "errors": {}}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"invalid existing oracle: {path}")
    data.setdefault("results", {})
    data.setdefault("errors", {})
    return data


def write_output(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary_path.replace(path)


def open_database(path: Path, threads: int) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect(":memory:")
    connection.execute(f"PRAGMA threads={threads}")
    escaped_path = str(path).replace("'", "''")
    connection.execute(f"ATTACH '{escaped_path}' AS benchmark_data (READ_ONLY)")
    table_names = [
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_catalog = 'benchmark_data' AND table_schema = 'main'"
        ).fetchall()
    ]
    if "__duckpgq_internal" not in table_names:
        connection.close()
        raise RuntimeError(f"DuckPGQ metadata table is missing from {path}")
    connection.execute(
        "CREATE TABLE __duckpgq_internal AS "
        "SELECT * FROM benchmark_data.main.__duckpgq_internal"
    )
    for table_name in table_names:
        if table_name == "__duckpgq_internal":
            continue
        escaped_table = table_name.replace('"', '""')
        connection.execute(
            f'CREATE VIEW "{escaped_table}" AS '
            f'SELECT rowid AS rowid, * FROM benchmark_data.main."{escaped_table}"'
        )
    try:
        connection.execute("LOAD duckpgq")
    except duckdb.Error:
        try:
            connection.execute("INSTALL duckpgq FROM community")
            connection.execute("LOAD duckpgq")
        except duckdb.Error as exc:
            connection.close()
            raise RuntimeError(
                "DuckPGQ could not be loaded or installed from the DuckDB community repository"
            ) from exc
    return connection


def main() -> int:
    args = parse_args()
    if duckdb.__version__ != "1.2.2":
        raise SystemExit(
            "oracle generation requires DuckDB 1.2.2 to match the installed DuckPGQ extension; "
            "run with .venv-duckpgq-oracle/bin/python"
        )
    selected_sfs = args.sf or sorted(DEFAULT_DATABASES)
    queries = [query for query in discover_queries(args.query_root) if query.category != "update"]
    if args.category:
        categories = set(args.category)
        queries = [query for query in queries if query.category in categories]
    if args.match:
        queries = [query for query in queries if args.match in query.rel_path]
    if args.limit:
        queries = queries[: args.limit]

    selected_paths = [query.rel_path for query in sorted(queries, key=lambda item: item.rel_path)]
    source_engine = f"DuckDB {duckdb.__version__} with DuckPGQ"
    if args.resume:
        existing = load_existing(args.output)
        resume_compatible = (
            existing.get("format_version") == ORACLE_FORMAT_VERSION
            and existing.get("source_engine") == source_engine
        )
        if resume_compatible:
            output = existing
            if (
                existing.get("source_query_suite_sha256")
                != query_suite_sha256(queries, args.query_root)
                or existing.get("query_paths") != selected_paths
            ):
                print(
                    "query suite changed; reusing only entries whose source SQL hash still matches",
                    flush=True,
                )
        else:
            print("existing oracle engine/format is incompatible; rebuilding selected entries", flush=True)
            output = {"results": {}, "errors": {}}
    else:
        output = {"results": {}, "errors": {}}
    output.update(
        {
            "format_version": ORACLE_FORMAT_VERSION,
            "source_engine": source_engine,
            "query_root": str(args.query_root),
            "query_suite_sha256": query_suite_sha256(queries),
            "source_query_root": str(args.query_root),
            "source_query_suite_sha256": query_suite_sha256(queries, args.query_root),
            "query_count": len(queries),
            "query_paths": [query.rel_path for query in sorted(queries, key=lambda item: item.rel_path)],
            "generated_at_unix": time.time(),
        }
    )
    write_output(args.output, output)
    results = output["results"]
    errors = output["errors"]
    assert isinstance(results, dict)
    assert isinstance(errors, dict)

    for sf in selected_sfs:
        database_path = DEFAULT_DATABASES[sf]
        if not database_path.exists():
            raise SystemExit(f"DuckDB reference database not found: {database_path}")
        sf_results = results.setdefault(sf, {})
        sf_errors = errors.setdefault(sf, {})
        assert isinstance(sf_results, dict)
        assert isinstance(sf_errors, dict)
        selected_path_set = set(selected_paths)
        for stale_path in set(sf_results) - selected_path_set:
            sf_results.pop(stale_path, None)
        for stale_path in set(sf_errors) - selected_path_set:
            sf_errors.pop(stale_path, None)
        write_output(args.output, output)
        connection = open_database(database_path, args.threads)
        try:
            for query_index, query in enumerate(queries, start=1):
                existing_entry = sf_results.get(query.rel_path)
                source_sql_sha256 = hashlib.sha256(query.path.read_bytes()).hexdigest()
                if (
                    args.resume
                    and isinstance(existing_entry, dict)
                    and "oracle_alias_of" not in existing_entry
                    and existing_entry.get("source_sql_sha256") == source_sql_sha256
                ):
                    sf_errors.pop(query.rel_path, None)
                    print(f"[{sf}] {query_index}/{len(queries)} SKIP {query.rel_path}", flush=True)
                    continue
                print(f"[{sf}] {query_index}/{len(queries)} {query.rel_path}", flush=True)
                try:
                    cursor = connection.execute(query.sql)
                    rows = cursor.fetchall()
                    columns = [item[0] for item in (cursor.description or [])]
                    canonical = canonical_rows(rows)
                    sf_results[query.rel_path] = {
                        "result_values_sha256": values_digest(rows),
                        "result_row_count": len(rows),
                        "columns": columns,
                        "canonical_values_preview": canonical[:5],
                        "source_sql_sha256": source_sql_sha256,
                    }
                    sf_errors.pop(query.rel_path, None)
                except Exception as exc:
                    sf_results.pop(query.rel_path, None)
                    sf_errors[query.rel_path] = f"{type(exc).__name__}: {exc}"
                write_output(args.output, output)
        finally:
            connection.close()
            write_output(args.output, output)
    return 0 if not any(errors.get(sf) for sf in selected_sfs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
