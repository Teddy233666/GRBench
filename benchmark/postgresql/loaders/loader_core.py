"""Shared schema, source-audit, and SQL planning for PostgreSQL/AGE loads."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


LOADERS_DIR = Path(__file__).resolve().parent
REPO_ROOT = LOADERS_DIR.parents[2]
SCHEMA_DIR = REPO_ROOT / "data" / "schema"
sys.path.insert(0, str(SCHEMA_DIR))
from sciscinet import DATA_PROFILE, EDGES, PLAINS, VERTICES


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
POSTGRES_TYPE_OVERRIDES = {
    ("Papers", "year"): "BIGINT",
    ("Papers", "date"): "DATE",
    ("Papers", "is_retracted"): "BOOLEAN",
    ("PaperDetails", "year"): "BIGINT",
    ("PaperDetails", "date"): "DATE",
    ("PaperDetails", "is_retracted"): "BOOLEAN",
    ("PaperDetails", "is_paratext"): "BOOLEAN",
    ("PaperReferences", "year"): "BIGINT",
    ("PaperReferences", "ref_year"): "BIGINT",
    ("hit_papers_level0", "year"): "BIGINT",
    ("hit_papers_level1", "year"): "BIGINT",
    ("normalized_citations_level0", "year"): "BIGINT",
    ("normalized_citations_level1", "year"): "BIGINT",
}
PLAIN_PRIMARY_KEYS = {"sources": "sourceid"}


@dataclass(frozen=True)
class TableSpec:
    name: str
    kind: str
    csv_name: str
    columns: tuple[tuple[str, str], ...]
    source_columns: tuple[tuple[str, str], ...]
    column_sources: tuple[tuple[str, str], ...]
    primary_key: str | None = None
    from_col: str | None = None
    to_col: str | None = None
    from_vertex: str | None = None
    to_vertex: str | None = None
    from_pk: str | None = None
    to_pk: str | None = None

    @property
    def requires_staging(self) -> bool:
        source_names = [name for name, _ in self.source_columns]
        selected_names = [source for _, source in self.column_sources]
        return source_names != selected_names


@dataclass(frozen=True)
class LoadStep:
    step_id: str
    table: str
    kind: str
    sql: str
    source_path: Path | None = None


def safe_identifier(value: str) -> str:
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"unsupported SQL identifier: {value!r}")
    return value


def quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def postgres_type(table: str, column: str, declared: str) -> str:
    value = POSTGRES_TYPE_OVERRIDES.get((table, column), declared).upper()
    return {"VARCHAR": "TEXT", "DOUBLE": "DOUBLE PRECISION"}.get(value, value)


def _table_spec(item: object, kind: str) -> TableSpec:
    name = safe_identifier(str(getattr(item, "name")))
    target_columns = tuple((safe_identifier(column), data_type) for column, data_type in getattr(item, "columns"))
    rename = {target: source for source, target in (getattr(item, "rename", None) or [])}
    csv_columns = getattr(item, "csv_columns", None)
    if csv_columns is None:
        csv_columns = [(rename.get(column, column), data_type) for column, data_type in target_columns]
    source_columns = tuple((column, data_type) for column, data_type in csv_columns)
    source_names = {column for column, _ in source_columns}
    column_sources = tuple((column, rename.get(column, column)) for column, _ in target_columns)
    for target, source in column_sources:
        if source not in source_names:
            raise ValueError(f"{name}.{target} maps to missing CSV column {source}")

    primary_key = getattr(item, "primary_key", None)
    if kind == "plain":
        primary_key = PLAIN_PRIMARY_KEYS.get(name)
    return TableSpec(
        name=name,
        kind=kind,
        csv_name=str(getattr(item, "csv")),
        columns=target_columns,
        source_columns=source_columns,
        column_sources=column_sources,
        primary_key=primary_key,
        from_col=getattr(item, "from_col", None),
        to_col=getattr(item, "to_col", None),
        from_vertex=getattr(item, "from_vertex", None),
        to_vertex=getattr(item, "to_vertex", None),
        from_pk=getattr(item, "from_pk", None),
        to_pk=getattr(item, "to_pk", None),
    )


def canonical_tables() -> list[TableSpec]:
    tables = [
        *(_table_spec(item, "vertex") for item in VERTICES),
        *(_table_spec(item, "edge") for item in EDGES),
        *(_table_spec(item, "plain") for item in PLAINS),
    ]
    names = [table.name.lower() for table in tables]
    if len(names) != len(set(names)):
        raise ValueError("canonical PostgreSQL table names are not unique")
    return tables


def source_csv_names(tables: Sequence[TableSpec] | None = None) -> list[str]:
    return sorted({table.csv_name for table in (tables or canonical_tables())})


def _index_name(table: str, column: str) -> str:
    base = f"grbench_{table}_{column}_idx".lower()
    if len(base) <= 63:
        return base
    digest = hashlib.sha256(base.encode()).hexdigest()[:10]
    return f"{base[:52]}_{digest}"


def index_columns(table: TableSpec) -> list[str]:
    columns = []
    for column, _ in table.columns:
        if column == table.primary_key:
            continue
        if table.kind == "edge" and column in {table.from_col, table.to_col}:
            columns.append(column)
        elif table.kind == "plain" and column.lower().endswith("id"):
            columns.append(column)
    return columns


def _target_ddl(table: TableSpec) -> str:
    definitions = []
    for column, declared_type in table.columns:
        definition = f"{safe_identifier(column)} {postgres_type(table.name, column, declared_type)}"
        definitions.append(definition)
    return f"CREATE TABLE {table.name} (\n    " + ",\n    ".join(definitions) + "\n);"


def _copy_command(
    table: str,
    columns: Iterable[str],
    path: Path,
    *,
    quote_columns: bool,
) -> str:
    column_list = ", ".join(
        quoted_identifier(column) if quote_columns else safe_identifier(column)
        for column in columns
    )
    return (
        f"\\copy {table} ({column_list}) FROM {sql_literal(path)} "
        "WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
    )


def _cast_expression(table: TableSpec, target: str, source: str) -> str:
    declared = dict(table.columns)[target]
    data_type = postgres_type(table.name, target, declared)
    source_sql = quoted_identifier(source)
    if data_type in {"TEXT", "VARCHAR"}:
        return source_sql
    return f"NULLIF(BTRIM({source_sql}), '')::{data_type}"


def relational_step(table: TableSpec, source_path: Path, rebuild: bool) -> LoadStep:
    statements = ["BEGIN;"]
    if rebuild:
        statements.append(f"DROP TABLE IF EXISTS {table.name} CASCADE;")
    statements.append(_target_ddl(table))
    if table.requires_staging:
        stage = safe_identifier(f"_grbench_stage_{table.name.lower()}")
        source_definitions = ", ".join(
            f"{quoted_identifier(column)} TEXT" for column, _ in table.source_columns
        )
        statements.append(f"CREATE TEMP TABLE {stage} ({source_definitions}) ON COMMIT DROP;")
        statements.append(
            _copy_command(
                stage,
                (column for column, _ in table.source_columns),
                source_path,
                quote_columns=True,
            )
        )
        targets = ", ".join(column for column, _ in table.columns)
        expressions = ", ".join(
            _cast_expression(table, target, source) for target, source in table.column_sources
        )
        statements.append(f"INSERT INTO {table.name} ({targets}) SELECT {expressions} FROM {stage};")
    else:
        statements.append(
            _copy_command(
                table.name,
                (column for column, _ in table.columns),
                source_path,
                quote_columns=False,
            )
        )
    if table.primary_key:
        constraint = _index_name(table.name, "pkey")
        statements.append(
            f"ALTER TABLE {table.name} ADD CONSTRAINT {constraint} "
            f"PRIMARY KEY ({safe_identifier(table.primary_key)});"
        )
    for column in index_columns(table):
        statements.append(
            f"CREATE INDEX {_index_name(table.name, column)} ON {table.name} ({column});"
        )
    statements.append("COMMIT;")
    return LoadStep(
        step_id=f"{table.kind}:{table.name}",
        table=table.name,
        kind=table.kind,
        sql="\n".join(statements) + "\n",
        source_path=source_path,
    )


def _age_session_prefix() -> str:
    return "LOAD 'age';\nSET search_path = ag_catalog, \"$user\", public;"


def age_graph_step(graph_name: str, rebuild: bool) -> LoadStep:
    graph_name = safe_identifier(graph_name)
    statements = ["CREATE EXTENSION IF NOT EXISTS age;", _age_session_prefix()]
    if rebuild:
        statements.append(
            f"SELECT drop_graph({sql_literal(graph_name)}, true) "
            f"WHERE to_regnamespace({sql_literal(graph_name)}) IS NOT NULL;"
        )
    statements.append(
        "DO $grbench$ BEGIN "
        f"IF to_regnamespace({sql_literal(graph_name)}) IS NULL THEN "
        f"PERFORM create_graph({sql_literal(graph_name)}); "
        "END IF; END $grbench$;"
    )
    return LoadStep(
        step_id="age:graph",
        table=graph_name,
        kind="graph",
        sql="\n".join(statements) + "\n",
    )


def age_label_step(
    table: TableSpec,
    graph_name: str,
    server_prepared_root: Path,
) -> LoadStep:
    graph_name = safe_identifier(graph_name)
    label_function = "create_vlabel" if table.kind == "vertex" else "create_elabel"
    loader_function = "load_labels_from_file" if table.kind == "vertex" else "load_edges_from_file"
    prepared_path = server_prepared_root / f"{table.name}.csv"
    regclass_name = f"{graph_name}.{quoted_identifier(table.name)}"
    statements = ["BEGIN;", _age_session_prefix()]
    statements.append(
        "DO $grbench$ BEGIN "
        f"IF to_regclass({sql_literal(regclass_name)}) IS NULL THEN "
        f"PERFORM {label_function}({sql_literal(graph_name)}, {sql_literal(table.name)}); "
        "END IF; END $grbench$;"
    )
    statements.append(
        f"SELECT {loader_function}({sql_literal(graph_name)}, {sql_literal(table.name)}, "
        f"{sql_literal(prepared_path)});"
    )
    schema = quoted_identifier(graph_name)
    label = quoted_identifier(table.name)
    if table.kind == "vertex" and table.primary_key:
        key = sql_literal(f'"{table.primary_key}"')
        statements.append(
            f"CREATE INDEX {_index_name(table.name, table.primary_key)} ON {schema}.{label} "
            f"(ag_catalog.agtype_access_operator(properties, {key}::agtype));"
        )
    elif table.kind == "edge":
        statements.append(
            f"CREATE INDEX {_index_name(table.name, 'start_id')} ON {schema}.{label} (start_id);"
        )
        statements.append(
            f"CREATE INDEX {_index_name(table.name, 'end_id')} ON {schema}.{label} (end_id);"
        )
    statements.append("COMMIT;")
    return LoadStep(
        step_id=f"{table.kind}:{table.name}",
        table=table.name,
        kind=table.kind,
        sql="\n".join(statements) + "\n",
        source_path=prepared_path,
    )


def build_load_steps(
    projection: str,
    sf: str,
    data_root: Path,
    prepared_root: Path,
    server_prepared_root: Path,
    graph_name: str,
    rebuild: bool,
) -> list[LoadStep]:
    if sf not in {f"sf10_{index}" for index in range(5)}:
        raise ValueError(f"unsupported scale factor: {sf}")
    tables = canonical_tables()
    data_dir = data_root / sf
    prepared_dir = prepared_root / f"{sf}_postgresql" / "age"
    server_prepared_dir = server_prepared_root / f"{sf}_postgresql" / "age"
    if projection == "relational":
        return [relational_step(table, data_dir / table.csv_name, rebuild) for table in tables]
    if projection != "age":
        raise ValueError(f"unsupported projection: {projection}")
    steps = [age_graph_step(graph_name, rebuild)]
    steps.extend(
        age_label_step(table, graph_name, server_prepared_dir)
        for table in tables
        if table.kind in {"vertex", "edge"}
    )
    steps.extend(
        relational_step(table, data_dir / table.csv_name, rebuild)
        for table in tables
        if table.kind == "plain"
    )
    return steps


def render_plan(steps: Sequence[LoadStep]) -> str:
    parts = []
    for step in steps:
        parts.append(f"-- GRBench load step: {step.step_id}\n{step.sql.rstrip()}\n")
    return "\n".join(parts)


def read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {path}") from exc


def scan_source_file(path: Path, full: bool) -> dict[str, object]:
    result: dict[str, object] = {"path": str(path), "bytes": path.stat().st_size}
    if not full:
        result["header"] = read_csv_header(path)
        return result
    digest = hashlib.sha256()

    class HashingReader(io.RawIOBase):
        def __init__(self, raw: io.FileIO):
            self.raw = raw

        def readable(self) -> bool:
            return True

        def readinto(self, buffer: bytearray) -> int:
            count = self.raw.readinto(buffer)
            if count:
                digest.update(memoryview(buffer)[:count])
            return count

        def close(self) -> None:
            try:
                self.raw.close()
            finally:
                super().close()

    with path.open("rb", buffering=0) as raw:
        buffered = io.BufferedReader(HashingReader(raw), buffer_size=8 * 1024 * 1024)
        with io.TextIOWrapper(buffered, encoding="utf-8-sig", newline="") as text:
            reader = csv.reader(text)
            try:
                result["header"] = next(reader)
            except StopIteration as exc:
                raise ValueError(f"empty CSV: {path}") from exc
            result["source_rows"] = sum(1 for _ in reader)
    result["sha256"] = digest.hexdigest()
    return result


def audit_source_files(
    data_dir: Path,
    tables: Sequence[TableSpec] | None = None,
    *,
    full: bool,
) -> dict[str, dict[str, object]]:
    tables = list(tables or canonical_tables())
    expected_headers: dict[str, list[str]] = {}
    for table in tables:
        header = [column for column, _ in table.source_columns]
        previous = expected_headers.setdefault(table.csv_name, header)
        if previous != header:
            raise ValueError(f"conflicting canonical headers for {table.csv_name}")
    inventory: dict[str, dict[str, object]] = {}
    for csv_name in sorted(expected_headers):
        path = data_dir / csv_name
        if not path.is_file():
            raise FileNotFoundError(f"missing canonical source CSV: {path}")
        result = scan_source_file(path, full)
        if result["header"] != expected_headers[csv_name]:
            raise ValueError(
                f"header mismatch for {path}: expected={expected_headers[csv_name]!r}, "
                f"actual={result['header']!r}"
            )
        inventory[csv_name] = result
    return inventory
