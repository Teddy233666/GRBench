#!/usr/bin/env python3
"""Repair known incomplete OrientDB native graph data-loaded databases.

The repairs are intentionally narrow:
- sf10_0: load the missing affiliated_with edge class with the current loader
  config.
- sf10_3: expose hit_papers_level1_export.csv as hit_papers_level1.csv, then
  load only the missing hit_papers_level1 document class.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Optional, Sequence

from credentials import orientdb_credentials, redact_orientdb_password


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
DEFAULT_DB_DIR = REPO_ROOT / ".local" / "orientdb" / "databases"
DEFAULT_DATA_ROOT = Path(os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / ".local" / "data"))
DEFAULT_UPDATE_DIR = REPO_ROOT / ".local" / "update-staging"
DEFAULT_QUERY_ROOT = ROOT / "queries"
DEFAULT_ORIENTDB_HOME = Path(os.environ.get("ORIENTDB_HOME", REPO_ROOT / ".local" / "orientdb-community-3.2.37"))
DEFAULT_JAVA_HOME = Path(os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-11-openjdk-amd64"))


def console_query(
    db_dir: Path,
    sf: str,
    sql: str,
    orientdb_home: Path,
    java_home: Path,
    heap: str,
) -> str:
    env = os.environ.copy()
    env["ORIENTDB_HOME"] = str(orientdb_home)
    env["JAVA_HOME"] = str(java_home)
    env.setdefault("LC_ALL", "C.UTF-8")
    env["ORIENTDB_OPTS_MEMORY"] = heap
    username, password = orientdb_credentials()
    commands = (
        f"set maxWidth 16384\n"
        f"connect plocal:{db_dir / sf} {username} {password}\n{sql}\nexit\n"
    )
    proc = subprocess.run(
        [str(orientdb_home / "bin" / "console.sh")],
        input=commands,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
        env=env,
        timeout=900,
    )
    safe_output = redact_orientdb_password(proc.stdout, password)
    if proc.returncode != 0:
        raise RuntimeError(safe_output)
    return safe_output


def manifest_has_class(
    db_dir: Path,
    sf: str,
    class_name: str,
    orientdb_home: Path,
    java_home: Path,
    heap: str,
) -> bool:
    output = console_query(
        db_dir,
        sf,
        f"select count(*) as n from _LoadManifest where class_name='{class_name}' and status='DONE'",
        orientdb_home,
        java_home,
        heap,
    )
    return "|0   |0   |" not in output


def ensure_sf10_3_hit_papers_alias(data_root: Path) -> None:
    data_dir = data_root / "sf10_3"
    target = data_dir / "hit_papers_level1.csv"
    source = data_dir / "hit_papers_level1_export.csv"
    if target.exists():
        return
    if not source.exists():
        raise FileNotFoundError(f"missing sf10_3 hit_papers_level1 source: {source}")
    target.symlink_to(source.name)
    print(f"[sf10_3] created {target} -> {source.name}", flush=True)


def run_loader(args: argparse.Namespace, sf: str, only_class: str) -> None:
    cmd = [
        "python3",
        str(ROOT / "load_orientdb_data.py"),
        "--sf",
        sf,
        "--db-dir",
        str(args.db_dir),
        "--data-root",
        str(args.data_root),
        "--update-dir",
        str(args.update_dir),
        "--query-root",
        str(args.query_root),
        "--orientdb-home",
        str(args.orientdb_home),
        "--java-home",
        str(args.java_home),
        "--heap",
        args.loader_heap,
        "--direct-memory",
        args.direct_memory,
        "--disk-cache-mb",
        str(args.disk_cache_mb),
        "--batch-size",
        str(args.batch_size),
        "--only-class",
        only_class,
        "--resume",
        "--skip-final-counts",
    ]
    if args.skip_source_count:
        cmd.append("--skip-source-count")
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def repair(args: argparse.Namespace) -> int:
    if args.skip_source_count:
        raise SystemExit(
            "strict native-graph repair cannot use --skip-source-count; "
            "the resulting database would not have verified source_rows provenance"
        )
    db_dir = Path(args.db_dir)
    data_root = Path(args.data_root)
    orientdb_home = Path(args.orientdb_home)
    java_home = Path(args.java_home)

    if "sf10_0" in args.sf:
        if manifest_has_class(db_dir, "sf10_0", "affiliated_with", orientdb_home, java_home, args.console_heap):
            print("[sf10_0] affiliated_with already DONE", flush=True)
        else:
            print("[sf10_0] loading missing affiliated_with", flush=True)
            run_loader(args, "sf10_0", "affiliated_with")

    if "sf10_3" in args.sf:
        ensure_sf10_3_hit_papers_alias(data_root)
        if manifest_has_class(db_dir, "sf10_3", "hit_papers_level1", orientdb_home, java_home, args.console_heap):
            print("[sf10_3] hit_papers_level1 already DONE", flush=True)
        else:
            print("[sf10_3] loading missing hit_papers_level1", flush=True)
            run_loader(args, "sf10_3", "hit_papers_level1")

    return 0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", action="append", choices=["sf10_0", "sf10_3"], default=[])
    parser.add_argument("--db-dir", default=str(DEFAULT_DB_DIR))
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--update-dir", default=str(DEFAULT_UPDATE_DIR))
    parser.add_argument("--query-root", default=str(DEFAULT_QUERY_ROOT))
    parser.add_argument("--orientdb-home", default=str(DEFAULT_ORIENTDB_HOME))
    parser.add_argument("--java-home", default=str(DEFAULT_JAVA_HOME))
    parser.add_argument("--loader-heap", default="32g")
    parser.add_argument("--direct-memory", default="32g")
    parser.add_argument("--disk-cache-mb", type=int, default=32768)
    parser.add_argument("--batch-size", type=int, default=50000)
    parser.add_argument("--console-heap", default="-Xms1G -Xmx8G")
    parser.add_argument("--skip-source-count", action="store_true")
    args = parser.parse_args(argv)
    if not args.sf:
        args.sf = ["sf10_0", "sf10_3"]
    return args


if __name__ == "__main__":
    raise SystemExit(repair(parse_args()))
