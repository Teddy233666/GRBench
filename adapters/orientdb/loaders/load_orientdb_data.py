#!/usr/bin/env python3
"""Load the GRBench SciSciNet data profile into OrientDB plocal databases."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

LOADER_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = LOADER_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
sys.path.insert(0, str(ADAPTER_DIR / "common"))
from credentials import orientdb_credentials, redact_orientdb_password


ROOT = ADAPTER_DIR
DEFAULT_ORIENTDB_HOME = Path(
    os.environ.get("ORIENTDB_HOME", REPO_ROOT / ".local" / "orientdb-community-3.2.37")
)
DEFAULT_JAVA_HOME = Path(
    os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-11-openjdk-amd64")
)
DEFAULT_DATA_ROOT = Path(
    os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / "data" / "processed")
)
DEFAULT_DB_ROOT = REPO_ROOT / ".local" / "orientdb" / "databases"
DEFAULT_QUERY_ROOT = ADAPTER_DIR / "queries"
DEFAULT_UPDATE_DIR = Path(
    os.environ.get("GRBENCH_UPDATE_DIR", REPO_ROOT / ".local" / "update-staging")
)
SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "sciscinet.py"
BUILD_DIR = REPO_ROOT / ".local" / "orientdb" / "build" / "loader"
CONFIG_DIR = BUILD_DIR / "config"

SCALE_FACTORS = ["sf10_0", "sf10_1", "sf10_2", "sf10_3", "sf10_4"]


def load_schema_module():
    schema_dir = str(SCHEMA_PATH.parent)
    sys.path.insert(0, schema_dir)
    try:
        import sciscinet  # type: ignore
    finally:
        try:
            sys.path.remove(schema_dir)
        except ValueError:
            pass
    return sciscinet


SCHEMA = load_schema_module()


def encode_cols(cols: Optional[Sequence[Tuple[str, str]]]) -> str:
    if not cols:
        return ""
    return ";".join(f"{name}:{typ}" for name, typ in cols)


def encode_rename(rename: Optional[Sequence[Tuple[str, str]]]) -> str:
    if not rename:
        return ""
    return ";".join(f"{old}>{new}" for old, new in rename)


def tsv_row(fields: Sequence[object]) -> str:
    out = []
    for field in fields:
        text = str(field)
        if any(ch in text for ch in "\t\r\n"):
            raise ValueError(f"TSV field contains control whitespace: {text!r}")
        out.append(text)
    return "\t".join(out)


def update_columns(update_dir: Path, name: str) -> List[Tuple[str, str]]:
    path = update_dir / f"{name}.csv"
    if not path.exists():
        return []
    header = path.open(encoding="utf-8", errors="replace").readline().strip()
    cols = [c.strip() for c in header.split(",") if c.strip()]
    return [(c, orient_type_for_column(c)) for c in cols]


def orient_type_for_column(column: str) -> str:
    c = column.lower()
    if c in {
        "cited_by_count",
        "reference_count",
        "citation_count",
        "c3",
        "c5",
        "c10",
        "team_size",
        "institution_count",
        "patent_count",
        "newsfeed_count",
        "nct_count",
        "nih_count",
        "nsf_count",
        "productivity",
        "h_index",
        "year_diff",
        "hit_1pct",
        "hit_5pct",
        "hit_10pct",
        "level",
        "works_count",
    }:
        return "LONG"
    if c in {
        "avg_c10",
        "avg_logc10",
        "p_gf",
        "p(gf)",
        "disruption",
        "atyp_median_z",
        "atyp_10pct_z",
        "atyp_pairs",
        "wsb_mu",
        "wsb_sigma",
        "wsb_cinf",
        "sb_b",
        "sb_t",
        "score_openalex",
        "normalized_citations",
        "c0",
    }:
        return "DOUBLE"
    return "STRING"


def normalized_columns(cols: Sequence[Tuple[str, str]]) -> List[Tuple[str, str]]:
    out = []
    for name, typ in cols:
        mapped = "STRING"
        if typ.upper() in {"BIGINT", "INTEGER", "INT", "LONG"}:
            mapped = "LONG"
        elif typ.upper() in {"DOUBLE", "FLOAT", "REAL"}:
            mapped = "DOUBLE"
        out.append((name, mapped))
    return out


def all_table_defs(update_dir: Path):
    rows = []
    for v in SCHEMA.VERTICES:
        rows.append(
            [
                "V",
                v.name,
                "DATA",
                v.csv,
                encode_cols(normalized_columns(v.columns)),
                encode_cols(normalized_columns(v.csv_columns or [])),
                encode_rename(v.rename),
                v.primary_key,
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    for e in SCHEMA.EDGES:
        edge_columns = list(normalized_columns(e.columns))
        rows.append(
            [
                "E",
                e.name,
                "DATA",
                e.csv,
                encode_cols(edge_columns),
                encode_cols(normalized_columns(e.csv_columns or [])),
                encode_rename(e.rename),
                "",
                e.from_col,
                e.to_col,
                e.from_vertex,
                e.to_vertex,
                e.from_pk,
                e.to_pk,
            ]
        )

    for p in SCHEMA.PLAINS:
        rows.append(
            [
                "P",
                p.name,
                "DATA",
                p.csv,
                encode_cols(normalized_columns(p.columns)),
                encode_cols(normalized_columns(p.csv_columns or [])),
                encode_rename(p.rename),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    columns_by_class = {str(row[1]): str(row[4]) for row in rows}
    update_targets = {
        "grbench_update1_papers": "Papers",
        "grbench_update1_papers_to_authors": "Papers_to_Authors",
        "grbench_update2_edges": "PaperReferences",
        "grbench_update3_contributed_from": "contributed_from",
        "grbench_update3_link_clinicaltrials": "Link_ClinicalTrials",
        "grbench_update3_link_newsfeed": "link_newsfeed",
        "grbench_update3_link_nih": "Link_NIH",
        "grbench_update3_link_nsf": "Link_NSF",
        "grbench_update3_link_twitter": "link_twitter",
        "grbench_update3_paperfields": "PaperFields",
        "grbench_update3_paperreferences": "PaperReferences",
        "grbench_update3_papers_to_authors": "Authors_Paper",
        "grbench_update4_authors_gender": "Authors_Gender",
        "grbench_update4_authors_paper": "Authors_Paper",
        "grbench_update5_papers_to_authors": "Papers_to_Authors",
        "grbench_update6_affiliated_with": "affiliated_with",
        "grbench_update6_papers_to_authors": "Papers_to_Authors",
    }
    update_renames = {
        "grbench_update1_papers": [
            ("c3", "C3"),
            ("c5", "C5"),
            ("c10", "C10"),
            ("atyp_median_z", "Atyp_Median_Z"),
            ("atyp_10pct_z", "Atyp_10pct_Z"),
            ("atyp_pairs", "Atyp_Pairs"),
            ("wsb_mu", "WSB_mu"),
            ("wsb_sigma", "WSB_sigma"),
            ("wsb_cinf", "WSB_Cinf"),
            ("sb_b", "SB_B"),
            ("sb_t", "SB_T"),
        ],
        "grbench_update3_contributed_from": [("institutionid", "institution_id")],
        "grbench_update4_authors_gender": [("P(gf)", "P_gf")],
    }
    for name, target in update_targets.items():
        rows.append(
            [
                "P",
                name,
                "UPDATE",
                f"{name}.csv",
                columns_by_class[target],
                "",
                encode_rename(update_renames.get(name, [])),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    # No separate CSV exists in the checked-in update data.  The SQL uses this
    # as the reverse author-paper delta, so load the same paper/author rows.
    rows.append(
        [
            "P",
            "grbench_update3_authors_paper",
            "UPDATE",
            "grbench_update3_papers_to_authors.csv",
            columns_by_class["Authors_Paper"],
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
    )

    return rows


def discover_index_columns(query_root: Path, rows: Sequence[Sequence[object]]) -> dict[str, set[str]]:
    sql = "\n".join(p.read_text(errors="replace") for p in query_root.rglob("*.sql")) if query_root.exists() else ""
    indexes: dict[str, set[str]] = {}
    for row in rows:
        name = str(row[1])
        cols = [part.split(":", 1)[0] for part in str(row[4]).split(";") if part]
        used = set()
        for col in cols:
            if re.search(rf"\b{re.escape(col)}\b", sql, re.IGNORECASE):
                used.add(col)
        if str(row[0]) == "V" and str(row[7]):
            used.add(str(row[7]))
        if str(row[0]) == "E":
            if str(row[8]):
                used.add(str(row[8]))
            if str(row[9]):
                used.add(str(row[9]))
        if used:
            indexes[name] = used
    return indexes


def write_config(update_dir: Path, query_root: Path) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    rows = all_table_defs(update_dir)
    header = [
        "kind",
        "name",
        "source",
        "csv",
        "columns",
        "csv_columns",
        "rename",
        "primary_key",
        "from_col",
        "to_col",
        "from_vertex",
        "to_vertex",
        "from_pk",
        "to_pk",
    ]
    (CONFIG_DIR / "tables.tsv").write_text(
        "\n".join([tsv_row(header)] + [tsv_row(row) for row in rows]) + "\n",
        encoding="utf-8",
    )
    indexes = discover_index_columns(query_root, rows)
    index_lines = ["class\tcolumns"]
    for cls in sorted(indexes):
        index_lines.append(tsv_row([cls, ";".join(sorted(indexes[cls]))]))
    (CONFIG_DIR / "indexes.tsv").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    manifest = {
        "generated_from": str(SCHEMA_PATH),
        "data_profile": SCHEMA.DATA_PROFILE,
        "update_dir": str(update_dir),
        "query_root": str(query_root),
        "table_count": len(rows),
        "index_class_count": len(indexes),
    }
    (CONFIG_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def compile_loader(java_home: Path, orientdb_home: Path) -> None:
    src = LOADER_DIR / "OrientDbCsvLoader.java"
    if not src.exists():
        raise SystemExit(f"Java loader source not found: {src}")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    classpath = f"{orientdb_home}/lib/*:{orientdb_home}/plugins/*"
    subprocess.run(
        [str(java_home / "bin" / "javac"), "-cp", classpath, "-d", str(BUILD_DIR), str(src)],
        check=True,
    )


def compatible_loader_config_sha256s() -> List[str]:
    compatibility_path = CONFIG_DIR / "compatible_loader_configs.json"
    if not compatibility_path.exists():
        return []
    compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    checksums: List[str] = []
    for item in compatibility.get("accepted_sha256s", []):
        checksum = str(item.get("sha256", "")) if isinstance(item, dict) else str(item)
        if checksum and checksum not in checksums:
            checksums.append(checksum)
    return checksums


def create_database_with_console(sf: str, db_root: Path, orientdb_home: Path, java_home: Path, rebuild: bool) -> None:
    db_path = db_root / sf
    if rebuild and db_path.exists():
        shutil.rmtree(db_path)
    if db_path.exists():
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["ORIENTDB_HOME"] = str(orientdb_home)
    env["JAVA_HOME"] = str(java_home)
    env.setdefault("LC_ALL", "C.UTF-8")
    username, password = orientdb_credentials()
    commands = (
        f"create database plocal:{db_path} {username} {password} plocal graph\nexit\n"
    )
    proc = subprocess.run(
        [str(orientdb_home / "bin" / "console.sh")],
        input=commands,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
        env=env,
        cwd=str(ROOT),
    )
    log_dir = REPO_ROOT / ".local" / "logs" / "orientdb" / "data-load" / sf
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_output = redact_orientdb_password(proc.stdout, password)
    (log_dir / "create_database.log").write_text(
        safe_output, encoding="utf-8", errors="replace"
    )
    if proc.returncode != 0 or "!ERROR:" in proc.stdout:
        raise RuntimeError(f"failed to create OrientDB database for {sf}; see {log_dir / 'create_database.log'}")


def run_loader(args: argparse.Namespace, sf: str) -> None:
    orientdb_home = Path(args.orientdb_home)
    java_home = Path(args.java_home)
    data_dir = Path(args.data_root) / sf
    if not data_dir.exists() or not any(data_dir.glob("*.csv")):
        print(f"[{sf}] skipped: no CSV files under {data_dir}", flush=True)
        return

    create_database_with_console(sf, Path(args.db_dir), orientdb_home, java_home, args.rebuild)

    cmd = [
        str(java_home / "bin" / "java"),
        "-Xms2g",
        f"-Xmx{args.heap}",
        f"-XX:MaxDirectMemorySize={args.direct_memory}",
        f"-Dstorage.diskCache.bufferSize={args.disk_cache_mb}",
        "-cp",
        f"{BUILD_DIR}:{orientdb_home}/lib/*:{orientdb_home}/plugins/*",
        "OrientDbCsvLoader",
        "--db-root",
        str(args.db_dir),
        "--sf",
        sf,
        "--data-dir",
        str(data_dir),
        "--update-dir",
        str(args.update_dir),
        "--config-dir",
        str(CONFIG_DIR),
        "--batch-size",
        str(args.batch_size),
        "--orphan-edge-mode",
        args.orphan_edge_mode,
        "--update-source-mode",
        args.update_source_mode,
    ]
    if args.rebuild:
        cmd.append("--rebuild")
    if args.skip_updates:
        cmd.append("--skip-updates")
    if args.skip_source_count:
        cmd.append("--skip-source-count")
    if args.skip_final_counts:
        cmd.append("--skip-final-counts")
    if args.resume:
        cmd.append("--resume")
    if args.repair_skipped_edges:
        cmd.append("--repair-skipped-edges")
    if args.derive_updates_only:
        cmd.append("--derive-updates-only")
    if args.derive_class:
        cmd.extend(["--derive-classes", ",".join(args.derive_class)])
    if args.resume_partial_edge_prefix:
        cmd.extend(
            [
                "--resume-partial-edge-prefixes",
                ",".join(args.resume_partial_edge_prefix),
            ]
        )
    compatible_config_sha256s = compatible_loader_config_sha256s()
    if compatible_config_sha256s:
        cmd.extend(
            [
                "--compatible-loader-config-sha256s",
                ",".join(compatible_config_sha256s),
            ]
        )
    if args.max_rows:
        cmd.extend(["--max-rows", str(args.max_rows)])
    if args.only_class:
        cmd.extend(["--only-class", args.only_class])

    env = os.environ.copy()
    env["ORIENTDB_HOME"] = str(orientdb_home)
    env["JAVA_HOME"] = str(java_home)
    env.setdefault("LC_ALL", "C.UTF-8")
    subprocess.run(cmd, check=True, env=env, cwd=str(ROOT))


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", action="append", choices=SCALE_FACTORS, help="Scale factor to load. Repeatable.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--db-dir", default=str(DEFAULT_DB_ROOT))
    parser.add_argument("--update-dir", default=str(DEFAULT_UPDATE_DIR))
    parser.add_argument("--query-root", default=str(DEFAULT_QUERY_ROOT))
    parser.add_argument("--orientdb-home", default=str(DEFAULT_ORIENTDB_HOME))
    parser.add_argument("--java-home", default=str(DEFAULT_JAVA_HOME))
    parser.add_argument("--heap", default="8g", help="Java max heap, e.g. 8g.")
    parser.add_argument(
        "--direct-memory",
        default="80g",
        help="Java max direct memory for OrientDB disk cache/native buffers, e.g. 80g.",
    )
    parser.add_argument(
        "--disk-cache-mb",
        type=int,
        default=65536,
        help="OrientDB storage.diskCache.bufferSize in MB.",
    )
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--max-rows", type=int, default=0, help="Smoke-test row cap per class; 0 loads all rows.")
    parser.add_argument("--skip-updates", action="store_true", help="Do not import grbench_update* delta tables.")
    parser.add_argument(
        "--skip-source-count",
        action="store_true",
        help="Do not pre-scan CSV files to count source rows before loading.",
    )
    parser.add_argument(
        "--skip-final-counts",
        action="store_true",
        help="Do not print final OrientDB class counts after loading.",
    )
    parser.add_argument("--rebuild", action="store_true", help="Drop/recreate the OrientDB database before loading.")
    parser.add_argument("--resume", action="store_true", help="Skip classes that were already fully loaded; reload partial edge classes.")
    parser.add_argument(
        "--resume-partial-edge-prefix",
        action="append",
        default=[],
        help=(
            "Preserve an explicitly named partial edge class and append after its committed "
            "source-row prefix. Requires --resume and placeholder orphan handling. Repeatable."
        ),
    )
    parser.add_argument(
        "--repair-skipped-edges",
        action="store_true",
        help="Keep existing edges and add only source rows whose endpoints require placeholders.",
    )
    parser.add_argument("--only-class", default="", help="Load only this configured OrientDB class.")
    parser.add_argument(
        "--orphan-edge-mode",
        choices=["placeholder", "skip"],
        default="placeholder",
        help="Preserve unresolved edge rows with _MissingEndpoint vertices, or skip them.",
    )
    parser.add_argument(
        "--update-source-mode",
        choices=["derived", "csv"],
        default="derived",
        help="Derive per-SF Update snapshots from the loaded baseline, or import legacy shared CSV files.",
    )
    parser.add_argument(
        "--derive-updates-only",
        action="store_true",
        help="Replace only Update staging classes with per-SF snapshots derived from the existing database.",
    )
    parser.add_argument(
        "--derive-class",
        action="append",
        default=[],
        help="Derive only this Update staging class; repeatable and used with --derive-updates-only.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.resume_partial_edge_prefix and not args.resume:
        raise SystemExit("--resume-partial-edge-prefix requires --resume")
    if args.resume_partial_edge_prefix and args.orphan_edge_mode != "placeholder":
        raise SystemExit(
            "--resume-partial-edge-prefix requires --orphan-edge-mode placeholder"
        )
    orientdb_home = Path(args.orientdb_home)
    java_home = Path(args.java_home)
    if not (orientdb_home / "lib" / "orientdb-core-3.2.37.jar").exists():
        raise SystemExit(f"OrientDB libraries not found under {orientdb_home}")
    if not (java_home / "bin" / "java").exists():
        raise SystemExit(f"Java not found under {java_home}")

    write_config(Path(args.update_dir), Path(args.query_root))
    compile_loader(java_home, orientdb_home)
    for sf in args.sf or SCALE_FACTORS:
        run_loader(args, sf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
