"""Prepare canonical SciSciNet CSVs for Apache AGE bulk label loading."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

from loader_core import DATA_PROFILE, TableSpec, canonical_tables, read_csv_header, scan_source_file


VERTEX_ID_COLUMNS = ("id",)
EDGE_ID_COLUMNS = ("start_id", "start_vertex_type", "end_id", "end_vertex_type")


def _plyvel():
    try:
        import plyvel
    except ImportError as exc:
        raise RuntimeError(
            "Apache AGE preparation requires plyvel and the system LevelDB development libraries"
        ) from exc
    return plyvel


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _remove_output(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _check_header(path: Path, table: TableSpec) -> None:
    expected = [column for column, _ in table.source_columns]
    actual = read_csv_header(path)
    if actual != expected:
        raise ValueError(f"header mismatch for {path}: expected={expected!r}, actual={actual!r}")


def _target_row(row: dict[str, str], table: TableSpec) -> dict[str, str]:
    return {target: row.get(source, "") for target, source in table.column_sources}


def prepare_vertex(
    table: TableSpec,
    source_path: Path,
    output_path: Path,
    mapping_path: Path | None,
    *,
    batch_size: int,
    overwrite: bool,
) -> dict[str, object]:
    if table.kind != "vertex" or not table.primary_key:
        raise ValueError(f"not an AGE vertex specification: {table.name}")
    _check_header(source_path, table)
    if output_path.exists() or (mapping_path is not None and mapping_path.exists()):
        if not overwrite:
            raise FileExistsError(f"prepared output exists for {table.name}; use --overwrite or --resume")
        _remove_output(output_path)
        if mapping_path is not None:
            _remove_output(mapping_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    database = None
    if mapping_path is not None:
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        database = _plyvel().DB(
            str(mapping_path),
            create_if_missing=True,
            write_buffer_size=64 * 1024 * 1024,
            max_open_files=1000,
            lru_cache_size=32 * 1024 * 1024,
            compression="snappy",
        )

    loaded_rows = 0
    try:
        with source_path.open(newline="", encoding="utf-8-sig") as source, output_path.open(
            "w", newline="", encoding="utf-8"
        ) as output:
            reader = csv.DictReader(source)
            fieldnames = [*VERTEX_ID_COLUMNS, *(column for column, _ in table.columns)]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            batch = database.write_batch() if database is not None else None
            pending_keys: set[bytes] = set()
            for graph_id, row in enumerate(reader, start=1):
                external_id = row.get(dict(table.column_sources)[table.primary_key], "")
                if not external_id:
                    raise ValueError(f"{table.name} row {graph_id + 1} has an empty primary key")
                if database is not None:
                    key = external_id.encode("utf-8")
                    if key in pending_keys or database.get(key) is not None:
                        raise ValueError(f"{table.name} has duplicate primary key {external_id!r}")
                    batch.put(key, str(graph_id).encode("ascii"))
                    pending_keys.add(key)
                writer.writerow({"id": graph_id, **_target_row(row, table)})
                loaded_rows += 1
                if batch is not None and loaded_rows % batch_size == 0:
                    batch.write()
                    batch = database.write_batch()
                    pending_keys.clear()
            if batch is not None and loaded_rows % batch_size:
                batch.write()
    finally:
        if database is not None:
            database.close()
    return {
        "table": table.name,
        "kind": table.kind,
        "source_path": str(source_path),
        "output_path": str(output_path),
        "mapping_path": str(mapping_path) if mapping_path is not None else "",
        "loaded_rows": loaded_rows,
        "skipped_rows": 0,
        "missing_start_rows": 0,
        "missing_end_rows": 0,
        "status": "DONE",
    }


def prepare_edge(
    table: TableSpec,
    source_path: Path,
    output_path: Path,
    start_mapping_path: Path,
    end_mapping_path: Path,
    *,
    batch_size: int,
    orphan_edge_mode: str,
    overwrite: bool,
) -> dict[str, object]:
    if table.kind != "edge" or not all(
        [table.from_col, table.to_col, table.from_vertex, table.to_vertex]
    ):
        raise ValueError(f"not an AGE edge specification: {table.name}")
    if orphan_edge_mode not in {"fail", "skip"}:
        raise ValueError(f"unsupported orphan edge mode: {orphan_edge_mode}")
    _check_header(source_path, table)
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(f"prepared output exists for {table.name}; use --overwrite or --resume")
        _remove_output(output_path)

    plyvel = _plyvel()
    if not start_mapping_path.is_dir() or not end_mapping_path.is_dir():
        raise FileNotFoundError(
            f"endpoint mappings are required for {table.name}: {start_mapping_path}, {end_mapping_path}"
        )
    start_db = plyvel.DB(str(start_mapping_path), create_if_missing=False)
    end_db = start_db if start_mapping_path == end_mapping_path else plyvel.DB(
        str(end_mapping_path), create_if_missing=False
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_rows = 0
    loaded_rows = 0
    skipped_rows = 0
    missing_start_rows = 0
    missing_end_rows = 0
    from_source = dict(table.column_sources)[str(table.from_col)]
    to_source = dict(table.column_sources)[str(table.to_col)]
    try:
        with source_path.open(newline="", encoding="utf-8-sig") as source, output_path.open(
            "w", newline="", encoding="utf-8"
        ) as output:
            reader = csv.DictReader(source)
            fieldnames = [*EDGE_ID_COLUMNS, *(column for column, _ in table.columns)]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row_number, row in enumerate(reader, start=2):
                source_rows += 1
                start_value = row.get(from_source, "")
                end_value = row.get(to_source, "")
                start_id = start_db.get(start_value.encode("utf-8")) if start_value else None
                end_id = end_db.get(end_value.encode("utf-8")) if end_value else None
                if start_id is None:
                    missing_start_rows += 1
                if end_id is None:
                    missing_end_rows += 1
                if start_id is None or end_id is None:
                    if orphan_edge_mode == "fail":
                        raise ValueError(
                            f"{table.name} row {row_number} has a missing endpoint: "
                            f"{table.from_vertex}.{start_value!r} -> {table.to_vertex}.{end_value!r}"
                        )
                    skipped_rows += 1
                    continue
                writer.writerow(
                    {
                        "start_id": start_id.decode("ascii"),
                        "start_vertex_type": table.from_vertex,
                        "end_id": end_id.decode("ascii"),
                        "end_vertex_type": table.to_vertex,
                        **_target_row(row, table),
                    }
                )
                loaded_rows += 1
                if batch_size and source_rows % batch_size == 0:
                    output.flush()
    finally:
        start_db.close()
        if end_db is not start_db:
            end_db.close()
    return {
        "table": table.name,
        "kind": table.kind,
        "source_path": str(source_path),
        "output_path": str(output_path),
        "mapping_path": "",
        "source_rows": source_rows,
        "loaded_rows": loaded_rows,
        "skipped_rows": skipped_rows,
        "missing_start_rows": missing_start_rows,
        "missing_end_rows": missing_end_rows,
        "status": "DONE",
    }


def _manifest_rows(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["table"]: row for row in manifest.get("tables", []) if isinstance(row, dict)}


def prepare_age_dataset(
    sf: str,
    data_root: Path,
    prepared_root: Path,
    *,
    batch_size: int,
    orphan_edge_mode: str,
    overwrite: bool,
    resume: bool,
    only_tables: Iterable[str] = (),
) -> Path:
    tables = canonical_tables()
    selected = {name.lower() for name in only_tables}
    unknown = selected - {table.name.lower() for table in tables if table.kind in {"vertex", "edge"}}
    if unknown:
        raise ValueError(f"unknown AGE table(s): {', '.join(sorted(unknown))}")
    if selected:
        selected_edges = [
            table for table in tables if table.kind == "edge" and table.name.lower() in selected
        ]
        selected.update(
            endpoint.lower()
            for table in selected_edges
            for endpoint in (str(table.from_vertex), str(table.to_vertex))
        )
    data_dir = data_root / sf
    output_dir = prepared_root / f"{sf}_postgresql" / "age"
    manifest_path = output_dir / "prepare_manifest.json"
    manifest: dict[str, Any] = {
        "profile": DATA_PROFILE,
        "sf": sf,
        "projection": "age",
        "orphan_edge_mode": orphan_edge_mode,
        "tables": [],
    }
    if resume and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("sf") != sf or manifest.get("orphan_edge_mode") != orphan_edge_mode:
            raise ValueError("existing AGE preparation manifest does not match the requested configuration")
    previous = _manifest_rows(manifest)
    rows: dict[str, dict[str, Any]] = dict(previous)
    endpoint_vertices = {
        endpoint
        for table in tables
        if table.kind == "edge"
        for endpoint in (table.from_vertex, table.to_vertex)
    }

    for table in tables:
        if table.kind != "vertex" or (selected and table.name.lower() not in selected):
            continue
        source_path = data_dir / table.csv_name
        source_audit = scan_source_file(source_path, full=True)
        existing = previous.get(table.name)
        output_path = output_dir / f"{table.name}.csv"
        mapping_path = output_dir / "maps" / f"{table.name}.leveldb" if table.name in endpoint_vertices else None
        if (
            resume
            and existing
            and existing.get("status") == "DONE"
            and existing.get("source_sha256") == source_audit.get("sha256")
            and output_path.is_file()
            and (mapping_path is None or mapping_path.is_dir())
        ):
            continue
        row = prepare_vertex(
            table,
            source_path,
            output_path,
            mapping_path,
            batch_size=batch_size,
            overwrite=overwrite or resume,
        )
        row.update(
            source_rows=source_audit["source_rows"],
            source_sha256=source_audit["sha256"],
            source_bytes=source_audit["bytes"],
        )
        rows[table.name] = row
        manifest["tables"] = [rows[name] for name in sorted(rows)]
        _atomic_write_json(manifest_path, manifest)

    for table in tables:
        if table.kind != "edge" or (selected and table.name.lower() not in selected):
            continue
        source_path = data_dir / table.csv_name
        source_audit = scan_source_file(source_path, full=True)
        existing = previous.get(table.name)
        output_path = output_dir / f"{table.name}.csv"
        if (
            resume
            and existing
            and existing.get("status") == "DONE"
            and existing.get("source_sha256") == source_audit.get("sha256")
            and output_path.is_file()
        ):
            continue
        row = prepare_edge(
            table,
            source_path,
            output_path,
            output_dir / "maps" / f"{table.from_vertex}.leveldb",
            output_dir / "maps" / f"{table.to_vertex}.leveldb",
            batch_size=batch_size,
            orphan_edge_mode=orphan_edge_mode,
            overwrite=overwrite or resume,
        )
        row.update(
            source_rows=source_audit["source_rows"],
            source_sha256=source_audit["sha256"],
            source_bytes=source_audit["bytes"],
        )
        rows[table.name] = row
        manifest["tables"] = [rows[name] for name in sorted(rows)]
        _atomic_write_json(manifest_path, manifest)

    manifest["tables"] = [rows[name] for name in sorted(rows)]
    _atomic_write_json(manifest_path, manifest)
    return manifest_path
