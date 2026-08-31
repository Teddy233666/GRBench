#!/usr/bin/env python3
"""OrientDB runner for the GRBench sciscinet query set.

The runner executes OrientDB SQL files against OrientDB 3.2.x through an
embedded worker in warm mode and records per-query status, timing, CPU, and
memory metrics.
It can create a schema-only database when the target database does not exist,
or run against a database already populated by load_orientdb_data.py.  Use a
data-loaded --load-mode value for full data benchmark runs.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import csv
import hashlib
import json
import os
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

import psutil

RUNNER_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = RUNNER_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
sys.path.insert(0, str(ADAPTER_DIR / "loaders"))
from credentials import orientdb_credentials, redact_orientdb_password


ROOT = ADAPTER_DIR
DEFAULT_ORIENTDB_HOME = Path(
    os.environ.get("ORIENTDB_HOME", REPO_ROOT / ".local" / "orientdb-community-3.2.37")
)
DEFAULT_JAVA_HOME = Path(
    os.environ.get("JAVA_HOME", "/usr/lib/jvm/java-11-openjdk-amd64")
)
DEFAULT_QUERY_ROOT = ADAPTER_DIR / "queries"
DEFAULT_SOURCE_QUERY_ROOT = REPO_ROOT / "benchmark" / "queries" / "canonical"
DEFAULT_DATA_ROOT = Path(
    os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / "data" / "processed")
)
DATA_ROOT = DEFAULT_DATA_ROOT
SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "sciscinet.py"

SCALE_FACTORS = ["sf10_0", "sf10_1", "sf10_2", "sf10_3", "sf10_4"]
CATEGORIES = [
    "High_Join_Relational_Graph_Hybrid_Queries",
    "Low_Join_Relational_Graph_Hybrid_Queries",
    "Pure_Graph_Queries",
    "Pure_Join_Queries",
    "Shortest_Path_Queries",
    "update",
]

QUERY_TIMEOUT_S = 18000
DEFAULT_CONSOLE_HEAP = "-Xms4G -Xmx16G"
DEFAULT_RESOURCE_SAMPLE_INTERVAL_S = 0.01
BENCHMARK_CONTRACT_VERSION = "grbench-cross-engine-v4-2026-07-20"
ORACLE_FORMAT_VERSION = "grbench-canonical-values-v2"
CONSOLE_MAX_WIDTH = 16_384
WORKER_SOURCE = RUNNER_DIR / "OrientDbBenchmarkWorker.java"
WORKER_BUILD_DIR = REPO_ROOT / ".local" / "orientdb" / "build" / "benchmark_worker"
LOADER_CONFIG_DIR = REPO_ROOT / ".local" / "orientdb" / "build" / "loader" / "config"
WORKER_PROTOCOL_VERSION = "4"
WORKER_STARTUP_TIMEOUT_S = 18000
WORKER_SHUTDOWN_TIMEOUT_S = 1800
WORKER_STARTUP_ATTEMPTS = 3
WORKER_STARTUP_RETRY_DELAY_S = 5
DEFAULT_WORKER_MAX_RESULT_ROWS = 1_000_000
DEFAULT_UPDATE_BATCH_SIZE = 10_000
DEFAULT_UPDATE_RECOVERY_MAX_ATTEMPTS = 12
UPDATE_ISOLATION_MODE = (
    "batched_commits_with_explicit_compensation_and_verified_baseline_v2"
)
UPDATE6_AUTHOR_SHADOW = "_GrbenchUpdate6AuthorShadow"
UPDATE_RECOVERY_PROGRESS = "_GrbenchUpdateRecoveryProgress"
UPDATE_WORKER_PROTOCOL = "native_batched_update_v4"

UPDATE_BATCH_OPERATIONS = {
    f"{number}{suffix}.sql": "DELETE" if suffix == "a" else "RESTORE"
    for number in range(1, 7)
    for suffix in ("a", "b")
}

UPDATE_SETUP_FILES = {
    "1b.sql": "1a.sql",
    "2b.sql": "2a.sql",
    "3b.sql": "3a.sql",
    "4b.sql": "4a.sql",
    "5b.sql": "5a.sql",
    "6b.sql": "6a.sql",
}

UPDATE_AFFECTED_CLASSES = {
    "1a.sql": [
        "PaperReferences",
        "Papers_to_Authors",
        "Authors_Paper",
        "contributed_from",
        "PaperFields",
        "Link_NSF",
        "Link_NIH",
        "Link_ClinicalTrials",
        "link_newsfeed",
        "link_twitter",
        "Papers",
    ],
    "1b.sql": [
        "PaperReferences",
        "Papers_to_Authors",
        "Authors_Paper",
        "contributed_from",
        "PaperFields",
        "Link_NSF",
        "Link_NIH",
        "Link_ClinicalTrials",
        "link_newsfeed",
        "link_twitter",
        "Papers",
    ],
    "2a.sql": ["PaperReferences"],
    "2b.sql": ["PaperReferences"],
    "3a.sql": [
        "PaperReferences",
        "Papers_to_Authors",
        "Authors_Paper",
        "contributed_from",
        "PaperFields",
        "Link_NSF",
        "Link_NIH",
        "Link_ClinicalTrials",
        "link_newsfeed",
        "link_twitter",
        "Papers",
    ],
    "3b.sql": [
        "PaperReferences",
        "Papers_to_Authors",
        "Authors_Paper",
        "contributed_from",
        "PaperFields",
        "Link_NSF",
        "Link_NIH",
        "Link_ClinicalTrials",
        "link_newsfeed",
        "link_twitter",
        "Papers",
    ],
    "4a.sql": ["Papers_to_Authors", "Authors_Paper", "affiliated_with", "Authors_Gender"],
    "4b.sql": ["Papers_to_Authors", "Authors_Paper", "affiliated_with", "Authors_Gender"],
    "5a.sql": ["Papers_to_Authors"],
    "5b.sql": ["Papers_to_Authors"],
    "6a.sql": [
        "Papers_to_Authors",
        "Authors_Paper",
        "affiliated_with",
        "Authors_Gender",
    ],
    "6b.sql": [
        "Papers_to_Authors",
        "Authors_Paper",
        "affiliated_with",
        "Authors_Gender",
    ],
}

UPDATE_SUPPORT_CLASSES = {
    filename: [UPDATE_RECOVERY_PROGRESS]
    for filename in UPDATE_BATCH_OPERATIONS
}
for _update6_file in ("6a.sql", "6b.sql"):
    UPDATE_SUPPORT_CLASSES[_update6_file].append(UPDATE6_AUTHOR_SHADOW)

UPDATE_COMPARABILITY_CLASS = {
    "1a.sql": "ORIENTDB_CASCADE_EXTENSION",
    "1b.sql": "ORIENTDB_CASCADE_EXTENSION",
    "4a.sql": "ORIENTDB_CASCADE_EXTENSION",
    "4b.sql": "ORIENTDB_CASCADE_EXTENSION",
}

UPDATE_CLASS_STAGING = {
    "1a.sql": {
        "PaperReferences": "grbench_update3_paperreferences",
        "Papers_to_Authors": "grbench_update1_papers_to_authors",
        "Authors_Paper": "grbench_update3_authors_paper",
        "contributed_from": "grbench_update3_contributed_from",
        "PaperFields": "grbench_update3_paperfields",
        "Link_NSF": "grbench_update3_link_nsf",
        "Link_NIH": "grbench_update3_link_nih",
        "Link_ClinicalTrials": "grbench_update3_link_clinicaltrials",
        "link_newsfeed": "grbench_update3_link_newsfeed",
        "link_twitter": "grbench_update3_link_twitter",
        "Papers": "grbench_update1_papers",
    },
    "2a.sql": {"PaperReferences": "grbench_update2_edges"},
    "3a.sql": {
        "PaperReferences": "grbench_update3_paperreferences",
        "Papers_to_Authors": "grbench_update1_papers_to_authors",
        "Authors_Paper": "grbench_update3_authors_paper",
        "contributed_from": "grbench_update3_contributed_from",
        "PaperFields": "grbench_update3_paperfields",
        "Link_NSF": "grbench_update3_link_nsf",
        "Link_NIH": "grbench_update3_link_nih",
        "Link_ClinicalTrials": "grbench_update3_link_clinicaltrials",
        "link_newsfeed": "grbench_update3_link_newsfeed",
        "link_twitter": "grbench_update3_link_twitter",
        "Papers": "grbench_update1_papers",
    },
    "4a.sql": {
        "Papers_to_Authors": "grbench_update6_papers_to_authors",
        "Authors_Paper": "grbench_update4_authors_paper",
        "affiliated_with": "grbench_update6_affiliated_with",
        "Authors_Gender": "grbench_update4_authors_gender",
    },
    "5a.sql": {"Papers_to_Authors": "grbench_update5_papers_to_authors"},
    "6a.sql": {
        "Papers_to_Authors": "grbench_update6_papers_to_authors",
        "affiliated_with": "grbench_update6_affiliated_with",
        "Authors_Gender": "grbench_update4_authors_gender",
    },
}
for _restore_file, _delete_file in UPDATE_SETUP_FILES.items():
    UPDATE_CLASS_STAGING[_restore_file] = UPDATE_CLASS_STAGING[_delete_file]

UPDATE_TARGET_SCOPES = {
    "1a.sql": [
        (
            "papers_2020_2025",
            "grbench_update1_papers",
            "SELECT count(*) AS benchmark_value FROM Papers WHERE year BETWEEN 2020 AND 2025",
        ),
    ],
    "2a.sql": [
        (
            "paperreferences_update2_keys",
            "grbench_update2_edges",
            "SELECT count(*) AS benchmark_value FROM PaperReferences "
            "WHERE citing_paperid IN "
            "(SELECT citing_paperid FROM grbench_update2_edges)",
        ),
    ],
    "3a.sql": [
        (
            "paperreferences_touching_cohort",
            "grbench_update3_paperreferences",
            "SELECT count(*) AS benchmark_value FROM PaperReferences "
            "WHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers) "
            "OR cited_paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "papers_to_authors_for_cohort",
            "grbench_update1_papers_to_authors",
            "SELECT count(*) AS benchmark_value FROM Papers_to_Authors "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "authors_paper_for_cohort",
            "grbench_update3_authors_paper",
            "SELECT count(*) AS benchmark_value FROM Authors_Paper "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "contributed_from_for_cohort",
            "grbench_update3_contributed_from",
            "SELECT count(*) AS benchmark_value FROM contributed_from "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "paperfields_for_cohort",
            "grbench_update3_paperfields",
            "SELECT count(*) AS benchmark_value FROM PaperFields "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "link_nsf_for_cohort",
            "grbench_update3_link_nsf",
            "SELECT count(*) AS benchmark_value FROM Link_NSF "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "link_nih_for_cohort",
            "grbench_update3_link_nih",
            "SELECT count(*) AS benchmark_value FROM Link_NIH "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "link_clinicaltrials_for_cohort",
            "grbench_update3_link_clinicaltrials",
            "SELECT count(*) AS benchmark_value FROM Link_ClinicalTrials "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "link_newsfeed_for_cohort",
            "grbench_update3_link_newsfeed",
            "SELECT count(*) AS benchmark_value FROM link_newsfeed "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "link_twitter_for_cohort",
            "grbench_update3_link_twitter",
            "SELECT count(*) AS benchmark_value FROM link_twitter "
            "WHERE paperid IN (SELECT paperid FROM grbench_update1_papers)",
        ),
        (
            "papers_2020_2025",
            "grbench_update1_papers",
            "SELECT count(*) AS benchmark_value FROM Papers WHERE year BETWEEN 2020 AND 2025",
        ),
    ],
    "4a.sql": [
        (
            "papers_to_authors_for_author_cohort",
            "grbench_update6_papers_to_authors",
            "SELECT count(*) AS benchmark_value FROM Papers_to_Authors "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
        (
            "authors_paper_for_author_cohort",
            "grbench_update4_authors_paper",
            "SELECT count(*) AS benchmark_value FROM Authors_Paper "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
        (
            "affiliated_with_for_author_cohort",
            "grbench_update6_affiliated_with",
            "SELECT count(*) AS benchmark_value FROM affiliated_with "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
        (
            "authors_h_index_10_20",
            "grbench_update4_authors_gender",
            "SELECT count(*) AS benchmark_value FROM Authors_Gender "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
    ],
    "5a.sql": [
        (
            "papers_to_authors_update5_keys",
            "grbench_update5_papers_to_authors",
            "SELECT count(*) AS benchmark_value FROM Papers_to_Authors "
            "WHERE paperid IN "
            "(SELECT paperid FROM grbench_update5_papers_to_authors)",
        ),
    ],
    "6a.sql": [
        (
            "papers_to_authors_for_author_cohort",
            "grbench_update6_papers_to_authors",
            "SELECT count(*) AS benchmark_value FROM Papers_to_Authors "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
        (
            "affiliated_with_for_author_cohort",
            "grbench_update6_affiliated_with",
            "SELECT count(*) AS benchmark_value FROM affiliated_with "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
        (
            "authors_in_author_cohort",
            "grbench_update4_authors_gender",
            "SELECT count(*) AS benchmark_value FROM Authors_Gender "
            "WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender)",
        ),
    ],
}
UPDATE_TARGET_SCOPES["1a.sql"] = UPDATE_TARGET_SCOPES["3a.sql"]
for _restore_file, _delete_file in UPDATE_SETUP_FILES.items():
    UPDATE_TARGET_SCOPES[_restore_file] = UPDATE_TARGET_SCOPES[_delete_file]


def normalize_console_heap(heap: str) -> str:
    text = (heap or "").strip()
    if not text:
        return ""
    if text.startswith("-X"):
        return text
    return f"-Xms4G -Xmx{text}"

def _load_schema_module():
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


SCHEMA = _load_schema_module()


def natural_key(text: str) -> Tuple[object, ...]:
    return tuple(int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text))


@dataclass
class QuerySpec:
    category: str
    subgroup: str
    rel_path: str
    path: Path
    sql: str


@dataclass
class Metrics:
    cpu_peak_pct: float = 0.0
    cpu_avg_pct: float = 0.0
    mem_peak_pct: float = 0.0
    mem_avg_pct: float = 0.0
    mem_peak_mb: float = 0.0
    mem_avg_mb: float = 0.0
    samples: int = 0
    cpu_time_sec: float = 0.0
    cpu_utilization_pct: float = 0.0


class ResourceMonitor:
    def __init__(self, pid: int, interval_s: float = DEFAULT_RESOURCE_SAMPLE_INTERVAL_S):
        self.pid = pid
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._cpu: List[float] = []
        self._mem_pct: List[float] = []
        self._mem_mb: List[float] = []
        self._total_mem = psutil.virtual_memory().total
        self._process_cache: Dict[int, psutil.Process] = {}
        self._started_at = 0.0
        self._start_cpu_seconds = 0.0

    def start(self) -> None:
        self._prime()
        self._start_cpu_seconds = self._cpu_seconds()
        self._started_at = time.monotonic()
        self._thread.start()

    def stop(self) -> Metrics:
        self._stop.set()
        self._thread.join(timeout=2)
        self._sample_once()
        elapsed = max(0.0, time.monotonic() - self._started_at)
        cpu_time = max(0.0, self._cpu_seconds() - self._start_cpu_seconds)
        metrics = self.metrics()
        metrics.cpu_time_sec = cpu_time
        metrics.cpu_utilization_pct = (cpu_time / elapsed * 100.0) if elapsed else 0.0
        metrics.cpu_avg_pct = metrics.cpu_utilization_pct
        return metrics

    def _processes(self) -> List[psutil.Process]:
        try:
            root = psutil.Process(self.pid)
            procs = [root] + root.children(recursive=True)
        except psutil.Error:
            return []
        cached: List[psutil.Process] = []
        live_pids = set()
        for proc in procs:
            pid = proc.pid
            live_pids.add(pid)
            cached_proc = self._process_cache.get(pid)
            if cached_proc is None:
                cached_proc = proc
                self._process_cache[pid] = cached_proc
            cached.append(cached_proc)
        for pid in list(self._process_cache):
            if pid not in live_pids:
                self._process_cache.pop(pid, None)
        return cached

    def _prime(self) -> None:
        for proc in self._processes():
            try:
                proc.cpu_percent(interval=None)
            except psutil.Error:
                pass

    def _cpu_seconds(self) -> float:
        total = 0.0
        for proc in self._processes():
            try:
                cpu_times = proc.cpu_times()
                total += cpu_times.user + cpu_times.system
            except psutil.Error:
                continue
        return total

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample_once()
            self._stop.wait(self.interval_s)

    def _sample_once(self) -> None:
        cpu = 0.0
        rss = 0
        for proc in self._processes():
            try:
                cpu += proc.cpu_percent(interval=None)
                rss += proc.memory_info().rss
            except psutil.Error:
                continue
        self._cpu.append(cpu)
        self._mem_mb.append(rss / (1024 * 1024))
        self._mem_pct.append((rss / self._total_mem) * 100 if self._total_mem else 0.0)

    def metrics(self) -> Metrics:
        if not self._cpu:
            return Metrics()
        return Metrics(
            cpu_peak_pct=max(self._cpu),
            cpu_avg_pct=sum(self._cpu) / len(self._cpu),
            mem_peak_pct=max(self._mem_pct),
            mem_avg_pct=sum(self._mem_pct) / len(self._mem_pct),
            mem_peak_mb=max(self._mem_mb),
            mem_avg_mb=sum(self._mem_mb) / len(self._mem_mb),
            samples=len(self._cpu),
        )


def kill_process_tree(pid: int) -> None:
    try:
        root = psutil.Process(pid)
        procs = root.children(recursive=True) + [root]
    except psutil.Error:
        return
    for proc in procs:
        try:
            proc.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(procs, timeout=5)
    for proc in alive:
        try:
            proc.kill()
        except psutil.Error:
            pass
    if alive:
        psutil.wait_procs(alive, timeout=30)


def discover_queries(query_root: Path) -> List[QuerySpec]:
    specs: List[QuerySpec] = []
    for category in CATEGORIES:
        root = query_root / category
        files = sorted(root.rglob("*.sql"), key=lambda p: natural_key(str(p.relative_to(root))))
        for path in files:
            rel = path.relative_to(query_root)
            parts = rel.parts
            subgroup = "/".join(parts[1:-1])
            specs.append(
                QuerySpec(
                    category=category,
                    subgroup=subgroup,
                    rel_path=str(rel),
                    path=path,
                    sql=path.read_text(errors="replace"),
                )
            )
    return specs


def query_suite_sha256(queries: Sequence[QuerySpec], root: Optional[Path] = None) -> str:
    digest = hashlib.sha256()
    for query in sorted(queries, key=lambda item: item.rel_path):
        path = root / query.rel_path if root is not None else query.path
        digest.update(query.rel_path.encode("utf-8"))
        digest.update(b"\0")
        if path.exists():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        else:
            digest.update(b"<MISSING>")
        digest.update(b"\0")
    return digest.hexdigest()


def split_sql_statements(sql: str) -> List[str]:
    def split_regular(chunk: str) -> List[str]:
        out: List[str] = []
        buf: List[str] = []
        in_single = False
        in_double = False
        i = 0
        while i < len(chunk):
            ch = chunk[i]
            if ch == "'" and not in_double:
                buf.append(ch)
                if in_single and i + 1 < len(chunk) and chunk[i + 1] == "'":
                    buf.append(chunk[i + 1])
                    i += 2
                    continue
                in_single = not in_single
                i += 1
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
            if ch == ";" and not in_single and not in_double:
                piece = "".join(buf).strip()
                if piece:
                    out.append(piece)
                buf = []
            else:
                buf.append(ch)
            i += 1
        piece = "".join(buf).strip()
        if piece:
            out.append(piece)
        return out

    statements: List[str] = []
    regular_lines: List[str] = []
    script_lines: List[str] = []
    in_script = False

    def flush_regular() -> None:
        nonlocal regular_lines
        if regular_lines:
            statements.extend(split_regular("\n".join(regular_lines)))
            regular_lines = []

    for line in sql.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if in_script:
            if lowered in {"end", "end;"}:
                script_lines.append("end")
                statements.append("\n".join(script_lines).strip())
                script_lines = []
                in_script = False
            else:
                script_lines.append(line)
            continue

        if lowered.startswith("script "):
            flush_regular()
            in_script = True
            script_lines = [line.rstrip(";")]
        else:
            regular_lines.append(line)

    if in_script and script_lines:
        statements.append("\n".join(script_lines).strip())
    flush_regular()
    return statements


def strip_sql_comments(sql: str) -> str:
    out: List[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if ch == "'" and not in_double:
            out.append(ch)
            if in_single and nxt == "'":
                out.append(nxt)
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if not in_single and not in_double and ch == "-" and nxt == "-":
            i += 2
            while i < len(sql) and sql[i] not in "\r\n":
                i += 1
            out.append(" ")
            continue
        if not in_single and not in_double and ch == "/" and nxt == "*":
            i += 2
            while i + 1 < len(sql) and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def collapse_sql_whitespace(sql: str) -> str:
    out: List[str] = []
    pending_space = False
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            if pending_space and out:
                out.append(" ")
                pending_space = False
            out.append(ch)
            if in_single and i + 1 < len(sql) and sql[i + 1] == "'":
                out.append(sql[i + 1])
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            if pending_space and out:
                out.append(" ")
                pending_space = False
            in_double = not in_double
            out.append(ch)
            i += 1
            continue
        if in_single or in_double:
            out.append(ch)
        elif ch.isspace():
            pending_space = True
        else:
            if pending_space and out:
                out.append(" ")
            pending_space = False
            out.append(ch)
        i += 1
    return "".join(out).strip()


def to_console_statement(sql: str) -> str:
    if sql.lstrip().lower().startswith("script "):
        return strip_sql_comments(sql).strip()
    return collapse_sql_whitespace(strip_sql_comments(sql))


def class_names_from_schema() -> List[Tuple[str, str]]:
    names: List[Tuple[str, str]] = []
    for vertex in SCHEMA.VERTICES:
        names.append((vertex.name, "V"))
    for edge in SCHEMA.EDGES:
        names.append((edge.name, "E"))
    for plain in SCHEMA.PLAINS:
        names.append((plain.name, ""))

    extras = [
        ("Link_Newsfeed", "E"),
        ("grbench_update1_papers", ""),
        ("grbench_update1_papers_to_authors", ""),
        ("grbench_update2_edges", ""),
        ("grbench_update3_authors_paper", ""),
        ("grbench_update3_contributed_from", ""),
        ("grbench_update3_link_clinicaltrials", ""),
        ("grbench_update3_link_newsfeed", ""),
        ("grbench_update3_link_nih", ""),
        ("grbench_update3_link_nsf", ""),
        ("grbench_update3_link_twitter", ""),
        ("grbench_update3_paperfields", ""),
        ("grbench_update3_paperreferences", ""),
        ("grbench_update3_papers_to_authors", ""),
        ("grbench_update4_authors_gender", ""),
        ("grbench_update4_authors_paper", ""),
        ("grbench_update5_papers_to_authors", ""),
        ("grbench_update6_affiliated_with", ""),
        ("grbench_update6_papers_to_authors", ""),
    ]
    names.extend(extras)

    seen = set()
    out: List[Tuple[str, str]] = []
    for name, parent in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((name, parent))
    return out


def console_env(orientdb_home: Path, java_home: Path, heap: str = "") -> Dict[str, str]:
    env = os.environ.copy()
    env["ORIENTDB_HOME"] = str(orientdb_home)
    env["JAVA_HOME"] = str(java_home)
    env["COLUMNS"] = str(CONSOLE_MAX_WIDTH)
    env.setdefault("LC_ALL", "C.UTF-8")
    if heap:
        env["ORIENTDB_OPTS_MEMORY"] = normalize_console_heap(heap)
    return env


def compile_benchmark_worker(java_home: Path, orientdb_home: Path) -> None:
    if not WORKER_SOURCE.exists():
        raise RuntimeError(f"OrientDB benchmark worker source is missing: {WORKER_SOURCE}")
    WORKER_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    class_file = WORKER_BUILD_DIR / "OrientDbBenchmarkWorker.class"
    if class_file.exists() and class_file.stat().st_mtime >= WORKER_SOURCE.stat().st_mtime:
        return
    classpath = f"{orientdb_home}/lib/*:{orientdb_home}/plugins/*"
    proc = subprocess.run(
        [
            str(java_home / "bin" / "javac"),
            "-cp",
            classpath,
            "-d",
            str(WORKER_BUILD_DIR),
            str(WORKER_SOURCE),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"failed to compile OrientDB benchmark worker:\n{proc.stdout}")


def worker_command(
    db_path: Path,
    orientdb_home: Path,
    java_home: Path,
    heap: str,
    max_result_rows: int,
) -> List[str]:
    classpath = f"{WORKER_BUILD_DIR}:{orientdb_home}/lib/*:{orientdb_home}/plugins/*"
    return [
        str(java_home / "bin" / "java"),
        *shlex.split(normalize_console_heap(heap)),
        "-Djna.nosys=true",
        f"-Djava.util.logging.config.file={orientdb_home}/config/orientdb-client-log.properties",
        "-Djava.awt.headless=true",
        "-Dfile.encoding=utf-8",
        "-cp",
        classpath,
        "OrientDbBenchmarkWorker",
        "--db-root",
        str(db_path.parent.resolve()),
        "--database",
        db_path.name,
        "--max-result-rows",
        str(max_result_rows),
    ]


def create_database(db_path: Path, orientdb_home: Path, java_home: Path, log_path: Path, rebuild: bool, heap: str) -> None:
    if rebuild and db_path.exists():
        shutil.rmtree(db_path)
    if db_path.exists():
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    username, password = orientdb_credentials()
    commands = [
        f"create database plocal:{db_path} {username} {password} plocal graph"
    ]
    for name, parent in class_names_from_schema():
        if parent:
            commands.append(f"create class {name} extends {parent} clusters 1")
        else:
            commands.append(f"create class {name} clusters 1")
    commands.append("exit")

    env = console_env(orientdb_home, java_home, heap)
    proc = subprocess.run(
        [str(orientdb_home / "bin" / "console.sh")],
        input="\n".join(commands) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(ROOT),
        env=env,
        timeout=900,
    )
    log_path.write_text(redact_orientdb_password(proc.stdout, password), errors="replace")
    if proc.returncode != 0 or "!ERROR:" in proc.stdout:
        raise RuntimeError(f"failed to create OrientDB schema at {db_path}; see {log_path}")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def data_manifest(sf: str, include_checksums: bool = True) -> Dict[str, object]:
    data_dir = DATA_ROOT / sf
    resolved = data_dir.resolve() if data_dir.exists() else data_dir
    files = sorted(data_dir.glob("*.csv")) if data_dir.exists() else []
    total = 0
    csvs = []
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        total += size
        if include_checksums:
            try:
                checksum = file_sha256(path)
                checksum_error = ""
            except OSError as exc:
                checksum = ""
                checksum_error = f"{type(exc).__name__}: {exc}"
        else:
            checksum = ""
            checksum_error = "not_requested"
        csvs.append(
            {
                "name": path.name,
                "path": str(path.resolve()),
                "bytes": size,
                "sha256": checksum,
                "sha256_error": checksum_error,
            }
        )
    return {
        "sf": sf,
        "data_dir": str(data_dir),
        "resolved_data_dir": str(resolved),
        "exists": data_dir.exists(),
        "csv_count": len(csvs),
        "total_csv_bytes": total,
        "csv_files": csvs,
    }


def query_load_manifest(
    sf: str,
    db_root: Path,
    orientdb_home: Path,
    java_home: Path,
    heap: str,
    log_path: Path,
) -> List[Dict[str, object]]:
    db_path = db_root / sf
    if not db_path.exists():
        return []
    fields = [
        "class_name",
        "status",
        "source_rows",
        "loaded_rows",
        "skipped_rows",
        "placeholder_rows",
        "orphan_edge_mode",
        "loader_mode",
        "source_kind",
        "source_file",
        "source_sha256",
        "source_rows_verified",
        "loader_config_sha256",
        "resume_mode",
        "resume_prefix_rows",
        "resume_prefix_assumption",
    ]
    query = "SELECT " + ",".join(fields) + " FROM _LoadManifest ORDER BY class_name LIMIT 1000"
    session = OrientDBWorkerSession(
        db_path=db_path,
        orientdb_home=orientdb_home,
        java_home=java_home,
        heap=heap,
        sample_interval_s=DEFAULT_RESOURCE_SAMPLE_INTERVAL_S,
        session_log_path=log_path,
        max_result_rows=10_000,
    )
    try:
        session.start()
        result = session.run_statements([query], timeout_s=900, measure_resources=False)
    except Exception as exc:
        return [{"sf": sf, "error": str(exc)}]
    finally:
        session.close()
    if result.status != "OK":
        return [{"sf": sf, "error": extract_first_error(result.output) or result.output[:1000]}]
    if not result.result_sets:
        return [{"sf": sf, "error": "_LoadManifest query returned no result set"}]
    result_set = result.result_sets[-1]
    columns = [str(value) for value in result_set.get("columns", [])]
    raw_rows = result_set.get("rows", [])
    if not isinstance(raw_rows, list):
        return [{"sf": sf, "error": "_LoadManifest result rows are malformed"}]
    rows: List[Dict[str, object]] = []
    for values in raw_rows:
        if not isinstance(values, list):
            continue
        row: Dict[str, object] = {"sf": sf}
        for field in fields:
            value = values[columns.index(field)] if field in columns and columns.index(field) < len(values) else None
            row[field] = "" if value is None else value
        rows.append(row)
    return rows


def is_true(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def source_fingerprint_index(data_manifests: Sequence[Dict[str, object]]) -> Dict[str, str]:
    fingerprints: Dict[str, str] = {}
    for manifest in data_manifests:
        if not isinstance(manifest, dict):
            continue
        for item in manifest.get("csv_files", []):
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            checksum = str(item.get("sha256", ""))
            if path and checksum:
                fingerprints[str(Path(path).resolve())] = checksum
    return fingerprints


def loader_config_sha256(config_dir: Path = LOADER_CONFIG_DIR) -> str:
    tables_path = config_dir / "tables.tsv"
    indexes_path = config_dir / "indexes.tsv"
    if not tables_path.exists() or not indexes_path.exists():
        return ""
    payload = (
        tables_path.read_text(encoding="utf-8")
        + "\n--indexes.tsv--\n"
        + indexes_path.read_text(encoding="utf-8")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compatible_loader_config_sha256s(config_dir: Path = LOADER_CONFIG_DIR) -> List[str]:
    current = loader_config_sha256(config_dir)
    tables_path = config_dir / "tables.tsv"
    indexes_path = config_dir / "indexes.tsv"
    if not current or not tables_path.exists() or not indexes_path.exists():
        return [current] if current else []
    tables_lines = tables_path.read_text(encoding="utf-8").splitlines(keepends=True)
    legacy_lines = [
        line for line in tables_lines if "\tgrbench_update4_authors_paper\t" not in line
    ]
    accepted = [current]
    if len(legacy_lines) != len(tables_lines):
        legacy_payload = (
            "".join(legacy_lines)
            + "\n--indexes.tsv--\n"
            + indexes_path.read_text(encoding="utf-8")
        )
        accepted.append(hashlib.sha256(legacy_payload.encode("utf-8")).hexdigest())
    compatibility_path = config_dir / "compatible_loader_configs.json"
    if compatibility_path.exists():
        compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
        for item in compatibility.get("accepted_sha256s", []):
            checksum = str(item.get("sha256", "")) if isinstance(item, dict) else str(item)
            if checksum and checksum not in accepted:
                accepted.append(checksum)
    return accepted


def validate_source_provenance(
    manifest_rows: List[Dict[str, object]],
    data_manifests: Sequence[Dict[str, object]],
    current_loader_config_sha256: str = "",
    accepted_loader_config_sha256s: Sequence[str] = (),
) -> Dict[str, object]:
    if not manifest_rows:
        return {"status": "NOT_APPLICABLE", "by_sf": {}, "problems": []}
    fingerprints = source_fingerprint_index(data_manifests)
    accepted_config_checksums = set(accepted_loader_config_sha256s)
    if current_loader_config_sha256:
        accepted_config_checksums.add(current_loader_config_sha256)
    by_sf: Dict[str, List[str]] = defaultdict(list)
    for row in manifest_rows:
        sf = str(row.get("sf", ""))
        source_kind = str(row.get("source_kind", ""))
        source_file = str(row.get("source_file", ""))
        stored_checksum = str(row.get("source_sha256", ""))
        stored_config_checksum = str(row.get("loader_config_sha256", ""))
        source_rows_verified = is_true(row.get("source_rows_verified", ""))
        if (
            not source_kind
            or not source_file
            or not stored_checksum
            or not source_rows_verified
            or not stored_config_checksum
            or not current_loader_config_sha256
            or stored_config_checksum not in accepted_config_checksums
        ):
            row["source_current_match"] = False
            by_sf[sf].append(f"{row.get('class_name', '')}:source_or_loader_provenance_mismatch")
            continue
        if source_kind == "derived_database_snapshot":
            row["source_current_match"] = True
            continue
        if source_kind != "csv":
            row["source_current_match"] = False
            by_sf[sf].append(f"{row.get('class_name', '')}:unknown_source_kind={source_kind}")
            continue
        try:
            source_path = str(Path(source_file).resolve())
        except OSError:
            source_path = source_file
        current_checksum = fingerprints.get(source_path)
        matches = bool(current_checksum) and current_checksum == stored_checksum
        row["source_current_match"] = matches
        if not matches:
            by_sf[sf].append(
                f"{row.get('class_name', '')}:source_sha256_mismatch"
                f":stored={stored_checksum},current={current_checksum or '<missing>'}"
            )
    sf_status = {}
    for sf, problems in by_sf.items():
        sf_status[sf] = {"status": "FAIL" if problems else "PASS", "problems": problems}
    for sf in {str(row.get("sf", "")) for row in manifest_rows}:
        sf_status.setdefault(sf, {"status": "PASS", "problems": []})
    return {
        "status": "PASS" if not any(by_sf.values()) else "FAIL",
        "by_sf": sf_status,
        "problems": [problem for problems in by_sf.values() for problem in problems],
    }


def orientdb_version(orientdb_home: Path, java_home: Path) -> str:
    env = console_env(orientdb_home, java_home)
    try:
        proc = subprocess.run(
            [str(orientdb_home / "bin" / "console.sh"), "help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            env=env,
        )
    except Exception as exc:
        return f"unknown ({exc})"
    first = proc.stdout.splitlines()[1:2]
    return first[0].strip() if first else "unknown"


def extract_first_error(output: str) -> str:
    lines = [line.strip() for line in output.splitlines()]
    capture: List[str] = []
    for i, line in enumerate(lines):
        if "!ERROR:" in line or line.startswith("Error parsing query") or "Exception" in line:
            capture = lines[i : i + 8]
            break
    if not capture:
        for line in lines:
            if line and not line.startswith("orientdb"):
                capture = [line]
                break
    text = " ".join(x for x in capture if x)
    text = re.sub(r"\s+", " ", text)
    return text[:1000]


CAUSE_DESCRIPTIONS = {
    "SCHEMA_ONLY_OK": (
        "The statement parsed/executed against the empty OrientDB schema. "
        "This is not a full data benchmark success because CSV data was not imported."
    ),
    "TIMEOUT": "Exceeded the configured per-query timeout and was terminated.",
    "UNSUPPORTED_SQL_PGQ_ANY_SHORTEST": (
        "The SQL uses SQL/PGQ ANY SHORTEST path syntax, which OrientDB 3.2 SQL does not support."
    ),
    "UNSUPPORTED_SQL_PGQ_GRAPH_TABLE": (
        "The SQL uses SQL/PGQ GRAPH_TABLE table functions, which OrientDB 3.2 SQL does not support."
    ),
    "UNSUPPORTED_ANSI_JOIN": (
        "The SQL uses ANSI JOIN syntax, which OrientDB SQL does not implement as relational joins."
    ),
    "MISSING_UPDATE_DELTA_TABLES": (
        "The update workload references grbench_update* delta tables that are not present in the dataset directories."
    ),
    "ORIENTDB_OOM": "OrientDB ran out of Java heap while executing the statement.",
    "UNSUPPORTED_INSERT_SELECT": "OrientDB rejected the INSERT ... SELECT form used by the update workload.",
    "ORIENTDB_CRASHED": "The OrientDB console process exited abnormally.",
    "ORIENTDB_ERROR": "OrientDB reported an error that did not match a more specific classifier.",
    "OK": "The statement completed successfully.",
}


def classify_cause_category(sql: str, output: str, status: str) -> str:
    if status == "OK":
        return "OK"
    if status == "SCHEMA_ONLY_OK":
        return "SCHEMA_ONLY_OK"
    if status == "TIMEOUT":
        return "TIMEOUT"
    if status == "CRASHED":
        return "ORIENTDB_CRASHED"
    low = sql.lower()
    out_low = output.lower()
    if "java heap space" in out_low or "outofmemoryerror" in out_low:
        return "ORIENTDB_OOM"
    if "any shortest" in low:
        return "UNSUPPORTED_SQL_PGQ_ANY_SHORTEST"
    if "graph_table" in low:
        return "UNSUPPORTED_SQL_PGQ_GRAPH_TABLE"
    if (
        "grbench_update" in low
        and ("class" in out_low or "cluster" in out_low or "table" in out_low)
        and ("not found" in out_low or "does not exist" in out_low or "not exist" in out_low)
    ):
        return "MISSING_UPDATE_DELTA_TABLES"
    if re.search(r"\binsert\s+into\b[\s\S]*\bselect\b", low):
        return "UNSUPPORTED_INSERT_SELECT"
    if re.search(r"\bjoin\b", low):
        return "UNSUPPORTED_ANSI_JOIN"
    return "ORIENTDB_ERROR"


def classify_cause(sql: str, output: str, status: str, sf: str) -> str:
    category = classify_cause_category(sql, output, status)
    if status == "OK":
        return ""
    if category == "SCHEMA_ONLY_OK":
        return CAUSE_DESCRIPTIONS[category]
    if category == "TIMEOUT":
        return CAUSE_DESCRIPTIONS[category]
    err = extract_first_error(output)
    if category == "UNSUPPORTED_SQL_PGQ_ANY_SHORTEST":
        return CAUSE_DESCRIPTIONS[category] + " " + err
    if category == "UNSUPPORTED_SQL_PGQ_GRAPH_TABLE":
        return CAUSE_DESCRIPTIONS[category] + " " + err
    if category == "UNSUPPORTED_ANSI_JOIN":
        return CAUSE_DESCRIPTIONS[category] + " " + err
    if category == "MISSING_UPDATE_DELTA_TABLES":
        return f"{CAUSE_DESCRIPTIONS[category]} Dataset checked: {DATA_ROOT / sf}. " + err
    if category == "ORIENTDB_OOM":
        return CAUSE_DESCRIPTIONS[category] + " " + err
    if category == "UNSUPPORTED_INSERT_SELECT":
        return CAUSE_DESCRIPTIONS[category] + " " + err
    if category == "ORIENTDB_CRASHED":
        return CAUSE_DESCRIPTIONS[category] + " " + err
    return err or "OrientDB reported an error, but no specific message was captured."


def safe_log_name(rel_path: str) -> str:
    out = rel_path.replace("/", "__").replace(" ", "_")
    out = re.sub(r"[^A-Za-z0-9_.=-]+", "_", out)
    return out + ".log"


def result_path_reference(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def query_statements(query: QuerySpec) -> List[str]:
    statements = [to_console_statement(s) for s in split_sql_statements(query.sql)]
    statements = [s for s in statements if s]
    if not statements:
        statements = [to_console_statement(query.sql)]
    return statements


def marker_statement(marker: str) -> str:
    return f"select '{marker}' as benchmark_marker;"


def parse_console_result_sets(output: str) -> List[Dict[str, object]]:
    lines = output.splitlines()
    result_sets: List[Dict[str, object]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("|#"):
            index += 1
            continue
        fields = [part.strip() for part in line.strip("|").split("|")]
        headers = fields[1:]
        index += 1
        if index < len(lines) and lines[index].strip().startswith("+"):
            index += 1
        rows: List[List[str]] = []
        while index < len(lines):
            row_line = lines[index].strip()
            if not row_line.startswith("|"):
                break
            values = [part.strip() for part in row_line.strip("|").split("|")]
            if values and values[0].isdigit():
                rows.append(values[1:])
            index += 1
        if headers != ["benchmark_marker"]:
            result_sets.append({"columns": headers, "rows": rows})
    return result_sets


def canonical_scalar_text(value: object) -> str:
    if value is None:
        return "<NULL>"
    text = str(value).strip()
    if not text or text.lower() in {"null", "none"}:
        return "<NULL>"
    if text.lower() in {"true", "false"}:
        return text.lower()
    if re.fullmatch(r"[+-]?\d+", text):
        return str(int(text))
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?", text):
        try:
            decimal_value = Decimal(text)
            normalized = format(decimal_value.normalize(), "f")
            return "0" if normalized in {"-0", "+0"} else normalized
        except InvalidOperation:
            pass
    return text


def canonical_result_summary(
    output: str,
    result_sets: Optional[Sequence[Dict[str, object]]] = None,
) -> Dict[str, object]:
    parsed_result_sets = list(result_sets) if result_sets is not None else parse_console_result_sets(output)
    canonical_sets = []
    canonical_values = []
    row_count = 0
    for result_set in parsed_result_sets:
        columns = [str(value) for value in result_set["columns"]]
        rows = [[canonical_scalar_text(value) for value in row] for row in result_set["rows"]]
        row_count += len(rows)
        sorted_rows = sorted(rows)
        canonical_sets.append({"columns": columns, "rows": sorted_rows})
        canonical_values.append(sorted_rows)
    encoded = json.dumps(canonical_sets, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    values_encoded = json.dumps(canonical_values, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    values_digest = hashlib.sha256(values_encoded.encode("utf-8")).hexdigest()
    preview = json.dumps(canonical_sets, ensure_ascii=False, separators=(",", ":"))[:1024]
    return {
        "result_set_count": len(canonical_sets),
        "result_row_count": row_count,
        "result_sha256": digest,
        "result_values_sha256": values_digest,
        "result_preview": preview,
        "result_canonicalization": (
            "typed_worker_values_rows_sorted_v2"
            if result_sets is not None
            else "console_tables_trimmed_rows_sorted_v1"
        ),
        "result_output_bytes": len(output.encode("utf-8", errors="replace")),
    }


def scalar_from_output(output: str, column: str = "benchmark_value") -> Optional[int]:
    for result_set in reversed(parse_console_result_sets(output)):
        headers = [str(value) for value in result_set["columns"]]
        if column not in headers or not result_set["rows"]:
            continue
        value = result_set["rows"][0][headers.index(column)]
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None
    return None


def scalar_from_result(result: QueryRunResult, column: str = "benchmark_value") -> Optional[int]:
    if result.result_sets:
        for result_set in reversed(result.result_sets):
            headers = [str(value) for value in result_set.get("columns", [])]
            rows = result_set.get("rows", [])
            if column not in headers or not isinstance(rows, list) or not rows:
                continue
            row = rows[0]
            if not isinstance(row, list):
                return None
            try:
                return int(row[headers.index(column)])
            except (IndexError, TypeError, ValueError):
                return None
        return None
    return scalar_from_output(result.output, column)


@dataclass
class QueryRunResult:
    status: str
    elapsed: float
    metrics: Metrics
    output: str
    timed_out: bool = False
    result_sets: List[Dict[str, object]] = field(default_factory=list)
    client_elapsed: float = 0.0


class OrientDBWorkerSession:
    def __init__(
        self,
        db_path: Path,
        orientdb_home: Path,
        java_home: Path,
        heap: str,
        sample_interval_s: float,
        session_log_path: Path,
        max_result_rows: int = DEFAULT_WORKER_MAX_RESULT_ROWS,
    ):
        self.db_path = db_path
        self.orientdb_home = orientdb_home
        self.java_home = java_home
        self.heap = heap
        self.sample_interval_s = sample_interval_s
        self.session_log_path = session_log_path
        self.max_result_rows = max_result_rows
        self.proc: Optional[subprocess.Popen[str]] = None
        self._lines: "queue.Queue[Optional[Tuple[List[str], float]]]" = queue.Queue()
        self._reader: Optional[threading.Thread] = None
        self._stderr_reader: Optional[threading.Thread] = None
        self._session_log = None
        self._log_lock = threading.Lock()

    def start(self) -> None:
        self.close()
        for attempt in range(1, WORKER_STARTUP_ATTEMPTS + 1):
            self.session_log_path.parent.mkdir(parents=True, exist_ok=True)
            self._session_log = self.session_log_path.open(
                "a", encoding="utf-8", errors="replace"
            )
            self._write_session_log(
                f"WORKER_START_ATTEMPT {attempt}/{WORKER_STARTUP_ATTEMPTS}\n"
            )
            env = console_env(self.orientdb_home, self.java_home, self.heap)
            self.proc = subprocess.Popen(
                worker_command(
                    self.db_path,
                    self.orientdb_home,
                    self.java_home,
                    self.heap,
                    self.max_result_rows,
                ),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=str(ROOT),
                env=env,
            )
            self._lines = queue.Queue()
            self._reader = threading.Thread(target=self._read_stdout, daemon=True)
            self._reader.start()
            self._stderr_reader = threading.Thread(target=self._read_stderr, daemon=True)
            self._stderr_reader.start()
            ready_message = self._wait_for_protocol(
                "GRBENCH_READY",
                request_id=None,
                timeout_s=WORKER_STARTUP_TIMEOUT_S,
            )
            ready = ready_message[0] if ready_message is not None else None
            if ready is not None and len(ready) >= 2:
                if ready[1] != WORKER_PROTOCOL_VERSION:
                    self.close(kill=True)
                    raise RuntimeError(
                        "OrientDB benchmark worker protocol mismatch: "
                        f"expected={WORKER_PROTOCOL_VERSION},actual={ready[1]}"
                    )
                return
            exit_code = self.proc.poll() if self.proc is not None else None
            self._write_session_log(
                f"WORKER_START_FAILED attempt={attempt} exit_code={exit_code}\n"
            )
            self.close(kill=True)
            if attempt < WORKER_STARTUP_ATTEMPTS:
                time.sleep(WORKER_STARTUP_RETRY_DELAY_S)
        raise RuntimeError(
            f"failed to establish OrientDB benchmark worker for {self.db_path} "
            f"after {WORKER_STARTUP_ATTEMPTS} attempts"
        )

    def close(self, kill: bool = False) -> None:
        proc = self.proc
        if proc is not None:
            if kill and proc.poll() is None:
                kill_process_tree(proc.pid)
            elif proc.poll() is None:
                try:
                    self._write("GRBENCH_CLOSE\n")
                except (BrokenPipeError, OSError):
                    pass
                try:
                    proc.wait(timeout=WORKER_SHUTDOWN_TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    self._write_session_log(
                        "WORKER_CLOSE_TIMEOUT "
                        f"timeout_sec={WORKER_SHUTDOWN_TIMEOUT_S}\n"
                    )
                    kill_process_tree(proc.pid)
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
        self.proc = None
        if self._reader is not None:
            self._reader.join(timeout=2)
        self._reader = None
        if self._stderr_reader is not None:
            self._stderr_reader.join(timeout=2)
        self._stderr_reader = None
        if self._session_log is not None:
            try:
                self._session_log.close()
            except Exception:
                pass
        self._session_log = None

    def restart(self) -> None:
        self.close(kill=True)
        self.start()

    def run_query(
        self,
        query: QuerySpec,
        timeout_s: int,
        measure_resources: bool = True,
    ) -> QueryRunResult:
        return self.run_statements(
            query_statements(query),
            timeout_s=timeout_s,
            measure_resources=measure_resources,
        )

    def run_statements(
        self,
        statements: Sequence[str],
        timeout_s: int,
        measure_resources: bool = True,
    ) -> QueryRunResult:
        request_id = str(time.time_ns())
        encoded_statements = [
            base64.b64encode(statement.encode("utf-8")).decode("ascii")
            for statement in statements
        ]
        request = "\t".join(
            ["GRBENCH_EXEC", request_id, str(len(encoded_statements)), *encoded_statements]
        ) + "\n"
        return self._run_request(
            request=request,
            request_id=request_id,
            timeout_s=timeout_s,
            measure_resources=measure_resources,
        )

    def run_update(
        self,
        filename: str,
        batch_size: int,
        mode: str,
        timeout_s: int,
        measure_resources: bool = True,
    ) -> QueryRunResult:
        if filename not in UPDATE_BATCH_OPERATIONS:
            raise ValueError(f"unsupported native Update file: {filename}")
        if batch_size < 1:
            raise ValueError("native Update batch size must be >= 1")
        if mode not in {"STRICT", "RECOVER", "RESTORE_ONLY", "FINALIZE_RECOVERY"}:
            raise ValueError(f"unsupported native Update mode: {mode}")
        request_id = str(time.time_ns())
        request = "\t".join(
            ["GRBENCH_UPDATE", request_id, filename, str(batch_size), mode]
        ) + "\n"
        return self._run_request(
            request=request,
            request_id=request_id,
            timeout_s=timeout_s,
            measure_resources=measure_resources,
        )

    def _run_request(
        self,
        request: str,
        request_id: str,
        timeout_s: int,
        measure_resources: bool,
    ) -> QueryRunResult:
        if self.proc is None or self.proc.poll() is not None:
            self.start()
        assert self.proc is not None
        request_sent_at = time.monotonic()
        try:
            self._write(request)
        except (BrokenPipeError, OSError) as exc:
            return QueryRunResult(
                status="CRASHED",
                elapsed=0.0,
                metrics=Metrics(),
                output=f"OrientDB worker write failed: {exc}",
            )

        started_message = self._wait_for_protocol("GRBENCH_START", request_id=request_id, timeout_s=120)
        if started_message is None:
            output = "OrientDB worker did not acknowledge the query start boundary"
            if self.proc.poll() is None:
                kill_process_tree(self.proc.pid)
            return QueryRunResult(status="CRASHED", elapsed=0.0, metrics=Metrics(), output=output)

        monitor = ResourceMonitor(self.proc.pid, interval_s=self.sample_interval_s) if measure_resources else None
        if monitor is not None:
            monitor.start()
        response_message = self._wait_for_protocol("GRBENCH_RESULT", request_id=request_id, timeout_s=timeout_s)
        response_received_at = time.monotonic()
        response = response_message[0] if response_message is not None else None
        client_elapsed = (
            response_message[1] - request_sent_at
            if response_message is not None
            else response_received_at - request_sent_at
        )
        metrics = monitor.stop() if monitor is not None else Metrics()
        if response is None:
            process_alive = self.proc.poll() is None
            if process_alive:
                kill_process_tree(self.proc.pid)
                return QueryRunResult(
                    status="TIMEOUT",
                    elapsed=float(timeout_s),
                    metrics=metrics,
                    output=f"OrientDB worker exceeded {timeout_s}s after the START boundary",
                    timed_out=True,
                    client_elapsed=client_elapsed,
                )
            return QueryRunResult(
                status="CRASHED",
                elapsed=client_elapsed,
                metrics=metrics,
                output="OrientDB worker exited before returning a result",
                client_elapsed=client_elapsed,
            )
        if len(response) < 6:
            return QueryRunResult(
                status="ERROR",
                elapsed=client_elapsed,
                metrics=metrics,
                output=f"invalid OrientDB worker response: {response}",
                client_elapsed=client_elapsed,
            )

        worker_status = response[2]
        try:
            elapsed = int(response[3]) / 1_000_000_000
            worker_cpu_time = int(response[4]) / 1_000_000_000
            payload_text = base64.b64decode(response[5]).decode("utf-8", errors="replace")
        except (ValueError, TypeError, binascii.Error) as exc:
            return QueryRunResult(
                status="ERROR",
                elapsed=client_elapsed,
                metrics=metrics,
                output=f"failed to decode OrientDB worker response: {exc}",
                client_elapsed=client_elapsed,
            )
        metrics.cpu_time_sec = worker_cpu_time
        metrics.cpu_utilization_pct = (worker_cpu_time / elapsed * 100.0) if elapsed else 0.0
        metrics.cpu_avg_pct = metrics.cpu_utilization_pct
        if worker_status != "OK":
            return QueryRunResult(
                status="ERROR",
                elapsed=elapsed,
                metrics=metrics,
                output=payload_text,
                client_elapsed=client_elapsed,
            )
        try:
            payload = json.loads(payload_text)
            result_sets = payload.get("result_sets", [])
            if not isinstance(result_sets, list):
                raise ValueError("result_sets is not a list")
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            return QueryRunResult(
                status="ERROR",
                elapsed=elapsed,
                metrics=metrics,
                output=f"invalid OrientDB worker JSON payload: {exc}",
                client_elapsed=client_elapsed,
            )
        return QueryRunResult(
            status="OK",
            elapsed=elapsed,
            metrics=metrics,
            output=payload_text + "\n",
            result_sets=result_sets,
            client_elapsed=client_elapsed,
        )

    def _read_stdout(self) -> None:
        assert self.proc is not None
        assert self.proc.stdout is not None
        try:
            for line in self.proc.stdout:
                stripped = line.rstrip("\r\n")
                if stripped.startswith("GRBENCH_"):
                    self._lines.put((stripped.split("\t"), time.monotonic()))
                else:
                    self._write_session_log(line)
        finally:
            self._lines.put(None)

    def _read_stderr(self) -> None:
        assert self.proc is not None
        assert self.proc.stderr is not None
        for line in self.proc.stderr:
            self._write_session_log(line)

    def _write(self, text: str) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise BrokenPipeError("OrientDB benchmark worker is not running")
        self.proc.stdin.write(text)
        self.proc.stdin.flush()

    def _wait_for_protocol(
        self,
        message_type: str,
        request_id: Optional[str],
        timeout_s: int,
    ) -> Optional[Tuple[List[str], float]]:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            remaining = max(0.0, min(0.2, deadline - time.monotonic()))
            try:
                message = self._lines.get(timeout=remaining)
            except queue.Empty:
                if self.proc is not None and self.proc.poll() is not None:
                    break
                continue
            if message is None:
                break
            fields, received_at = message
            if not fields or fields[0] != message_type:
                self._write_session_log("PROTOCOL_UNEXPECTED " + repr(fields) + "\n")
                continue
            if request_id is not None and (len(fields) < 2 or fields[1] != request_id):
                self._write_session_log("PROTOCOL_REQUEST_MISMATCH " + repr(fields) + "\n")
                continue
            return fields, received_at
        return None

    def _write_session_log(self, output: str) -> None:
        if self._session_log is None or not output:
            return
        with self._log_lock:
            self._session_log.write(output)
            self._session_log.flush()


OrientDBConsoleSession = OrientDBWorkerSession


def row_from_result(
    sf: str,
    query: QuerySpec,
    status: str,
    output: str,
    elapsed: float,
    metrics: Metrics,
    log_rel: str,
    runs: int = 1,
    run_elapsed_sec: Optional[Sequence[float]] = None,
    result_sets: Optional[Sequence[Dict[str, object]]] = None,
    client_elapsed: float = 0.0,
    run_client_elapsed_sec: Optional[Sequence[float]] = None,
    execution_backend: str = "embedded_worker",
    source_query_root: Path = DEFAULT_SOURCE_QUERY_ROOT,
) -> Dict[str, object]:
    cause_category = classify_cause_category(query.sql, output, status)
    cause = classify_cause(query.sql, output, status, sf)
    result_summary = canonical_result_summary(output, result_sets=result_sets)
    elapsed_value: object = round(elapsed, 6)
    rounded_run_elapsed = [round(x, 6) for x in (run_elapsed_sec or [])]
    rounded_client_elapsed = [round(x, 6) for x in (run_client_elapsed_sec or [])]
    source_path = source_query_root / query.rel_path
    row = {
        "sf": sf,
        "category": query.category,
        "subgroup": query.subgroup,
        "sql_file": query.rel_path,
        "status": status,
        "elapsed_sec": elapsed_value,
        "time_sec": elapsed_value,
        "median_execution_time_seconds": elapsed_value,
        "client_elapsed_sec": round(client_elapsed, 6),
        "runs": runs,
        "metric_aggregation": "single_run" if runs == 1 else "median_elapsed_run",
        "metric_window": (
            "worker_pre_execute_to_fully_materialized_result"
            if execution_backend == "embedded_worker"
            else "cold_console_process_end_to_end"
        ),
        "execution_backend": execution_backend,
        "run_elapsed_sec": json.dumps(rounded_run_elapsed),
        "run_client_elapsed_sec": json.dumps(rounded_client_elapsed),
        "cpu_peak": round(metrics.cpu_peak_pct, 6),
        "cpu_avg": round(metrics.cpu_avg_pct, 6),
        "cpu_peak_pct": round(metrics.cpu_peak_pct, 6),
        "cpu_avg_pct": round(metrics.cpu_avg_pct, 6),
        "mem_peak_pct": round(metrics.mem_peak_pct, 6),
        "mem_avg_pct": round(metrics.mem_avg_pct, 6),
        "mem_peak_mb": round(metrics.mem_peak_mb, 6),
        "mem_avg_mb": round(metrics.mem_avg_mb, 6),
        "samples": metrics.samples,
        "cpu_time_sec": round(metrics.cpu_time_sec, 9),
        "cpu_utilization_pct": round(metrics.cpu_utilization_pct, 6),
        "cause_category": cause_category,
        "error_cause": cause,
        "first_error": extract_first_error(output) if status in {"ERROR", "TIMEOUT", "CRASHED"} else "",
        "log_file": log_rel,
        "benchmark_contract_version": BENCHMARK_CONTRACT_VERSION,
        "query_sql_sha256": hashlib.sha256(query.sql.encode("utf-8")).hexdigest(),
        "source_query_sql_sha256": (
            hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path.exists() else ""
        ),
    }
    row.update(result_summary)
    return row


def median_run_index(runs: Sequence[QueryRunResult]) -> int:
    if not runs:
        return 0
    ordered = sorted(range(len(runs)), key=lambda i: runs[i].elapsed)
    return ordered[len(ordered) // 2]


def run_query_file_warm(
    sf: str,
    query: QuerySpec,
    session: OrientDBConsoleSession,
    log_dir: Path,
    timeout_s: int,
    success_status: str,
    runs: int,
    warmup_runs: int,
    source_query_root: Path = DEFAULT_SOURCE_QUERY_ROOT,
) -> Dict[str, object]:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / safe_log_name(query.rel_path)
    warmup_results: List[QueryRunResult] = []
    run_results: List[QueryRunResult] = []
    for _warmup_index in range(warmup_runs):
        result = session.run_query(query, timeout_s=timeout_s, measure_resources=False)
        warmup_results.append(result)
        if result.status in {"TIMEOUT", "CRASHED"}:
            session.restart()
        if result.status != "OK":
            break
    warmup_ok = all(result.status == "OK" for result in warmup_results) and len(warmup_results) == warmup_runs
    if warmup_ok:
        for _run_idx in range(runs):
            result = session.run_query(query, timeout_s=timeout_s)
            run_results.append(result)
            if result.status in {"TIMEOUT", "CRASHED"}:
                session.restart()
            if result.status != "OK":
                break

    selected_pool = run_results or warmup_results or [empty_run_result("ERROR", "no query execution occurred")]
    selected = selected_pool[median_run_index(selected_pool)]
    statuses = [result.status for result in selected_pool]
    if "TIMEOUT" in statuses:
        status = "TIMEOUT"
    elif "CRASHED" in statuses:
        status = "CRASHED"
    elif not warmup_ok or any(run_status != "OK" for run_status in statuses):
        status = "ERROR"
    else:
        status = success_status

    output_parts = []
    for index, result in enumerate(warmup_results, start=1):
        output_parts.append(
            f"--- WARMUP {index} status={result.status} elapsed={result.elapsed:.6f}s ---\n"
        )
        output_parts.append(result.output)
        if result.output and not result.output.endswith("\n"):
            output_parts.append("\n")
    for index, result in enumerate(run_results, start=1):
        output_parts.append(f"--- RUN {index} status={result.status} elapsed={result.elapsed:.6f}s ---\n")
        output_parts.append(result.output)
        if result.output and not result.output.endswith("\n"):
            output_parts.append("\n")
    output = "".join(output_parts)
    log_path.write_text(output, errors="replace")
    elapsed = timeout_s if status == "TIMEOUT" else selected.elapsed
    row = row_from_result(
        sf=sf,
        query=query,
        status=status,
        output=selected.output,
        elapsed=elapsed,
        metrics=selected.metrics,
        log_rel=result_path_reference(log_path),
        runs=len(run_results),
        run_elapsed_sec=[result.elapsed for result in run_results],
        result_sets=selected.result_sets,
        client_elapsed=selected.client_elapsed,
        run_client_elapsed_sec=[result.client_elapsed for result in run_results],
        source_query_root=source_query_root,
    )
    row["warmup_runs_requested"] = warmup_runs
    row["warmup_runs_completed"] = len(warmup_results)
    row["warmup_status"] = "PASS" if warmup_ok else "FAIL"
    return row


def query_from_sibling(query: QuerySpec, filename: str) -> QuerySpec:
    path = query.path.with_name(filename)
    rel_path = str(Path(query.rel_path).with_name(filename))
    return QuerySpec(
        category=query.category,
        subgroup=query.subgroup,
        rel_path=rel_path,
        path=path,
        sql=path.read_text(errors="replace"),
    )


def class_count_statement(classes: Sequence[str]) -> str:
    aliases = [f"c{index}" for index in range(len(classes))]
    projection = ", ".join(f"$q{index}[0].v AS {alias}" for index, alias in enumerate(aliases))
    lets = ", ".join(
        f"$q{index} = (SELECT count(*) AS v FROM {class_name})"
        for index, class_name in enumerate(classes)
    )
    return f"SELECT {projection} LET {lets}"


def class_counts_from_output(
    output: str,
    classes: Sequence[str],
    result_sets: Optional[Sequence[Dict[str, object]]] = None,
) -> Optional[Dict[str, int]]:
    parsed_result_sets = list(result_sets) if result_sets is not None else parse_console_result_sets(output)
    if not parsed_result_sets:
        return None
    result_set = parsed_result_sets[-1]
    headers = [str(value) for value in result_set["columns"]]
    rows = result_set["rows"]
    if not rows:
        return None
    counts: Dict[str, int] = {}
    for index, class_name in enumerate(classes):
        alias = f"c{index}"
        if alias not in headers:
            return None
        try:
            counts[class_name] = int(str(rows[0][headers.index(alias)]).strip())
        except (IndexError, TypeError, ValueError):
            return None
    return counts


def read_class_counts(
    session: OrientDBConsoleSession,
    classes: Sequence[str],
    timeout_s: int,
) -> Tuple[QueryRunResult, Optional[Dict[str, int]]]:
    result = session.run_statements(
        [class_count_statement(classes)],
        timeout_s=timeout_s,
        measure_resources=False,
    )
    return (
        result,
        class_counts_from_output(result.output, classes, result.result_sets)
        if result.status == "OK"
        else None,
    )


def manifest_loaded_counts(manifest_rows: Sequence[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in manifest_rows:
        class_name = str(row.get("class_name", ""))
        try:
            counts[class_name] = int(str(row.get("loaded_rows", "")).strip())
        except ValueError:
            continue
    return counts


def query_dependencies(query: QuerySpec) -> List[str]:
    return [
        class_name
        for class_name, _parent in class_names_from_schema()
        if re.search(rf"\b{re.escape(class_name)}\b", query.sql, flags=re.IGNORECASE)
    ]


def read_class_counts_batched(
    session: OrientDBConsoleSession,
    classes: Sequence[str],
    timeout_s: int,
    batch_size: int = 12,
) -> Tuple[str, Dict[str, int], str]:
    counts: Dict[str, int] = {}
    outputs = []
    for offset in range(0, len(classes), batch_size):
        batch = classes[offset : offset + batch_size]
        result, batch_counts = read_class_counts(session, batch, timeout_s)
        outputs.append(result.output)
        if result.status != "OK" or batch_counts is None:
            return result.status, counts, "".join(outputs)
        counts.update(batch_counts)
    return "OK", counts, "".join(outputs)


def database_preflight(
    session: OrientDBConsoleSession,
    queries: Sequence[QuerySpec],
    manifest_rows: Sequence[Dict[str, object]],
    timeout_s: int,
) -> Dict[str, object]:
    dependencies = sorted(
        {dependency for query in queries for dependency in query_dependencies(query)},
        key=str.lower,
    )
    status, database_counts, output = read_class_counts_batched(
        session,
        dependencies,
        timeout_s,
    )
    support_classes = [UPDATE6_AUTHOR_SHADOW, UPDATE_RECOVERY_PROGRESS]
    support_status, support_counts, support_output = read_class_counts_batched(
        session,
        support_classes,
        timeout_s,
    )
    support_problems = []
    if support_status != "OK":
        support_problems.append(f"support_count_status={support_status}")
    else:
        for class_name in support_classes:
            if support_counts.get(class_name) != 0:
                support_problems.append(
                    f"{class_name}:database={support_counts.get(class_name)},expected=0"
                )
    expected_counts = manifest_loaded_counts(manifest_rows)
    baseline_mismatches = []
    data_incomplete = []
    manifest_by_class = {
        str(row.get("class_name", "")): row
        for row in manifest_rows
        if row.get("class_name")
    }
    for class_name in dependencies:
        expected = expected_counts.get(class_name)
        actual = database_counts.get(class_name)
        if expected is None:
            baseline_mismatches.append(f"{class_name}:missing_manifest")
        elif actual != expected:
            baseline_mismatches.append(f"{class_name}:database={actual},manifest={expected}")
        row = manifest_by_class.get(class_name)
        if row is None:
            continue
        try:
            source_rows = int(str(row.get("source_rows", "0") or "0"))
            loaded_rows = int(str(row.get("loaded_rows", "0") or "0"))
            skipped_rows = int(str(row.get("skipped_rows", "0") or "0"))
        except ValueError:
            data_incomplete.append(f"{class_name}:invalid_manifest_counts")
            continue
        if source_rows != loaded_rows or skipped_rows != 0:
            data_incomplete.append(
                f"{class_name}:source={source_rows},loaded={loaded_rows},skipped={skipped_rows}"
            )
        if not is_true(row.get("source_rows_verified", "")):
            data_incomplete.append(f"{class_name}:source_rows_not_verified")
        if not is_true(row.get("source_current_match", "")):
            data_incomplete.append(f"{class_name}:source_fingerprint_mismatch")
    passed = (
        status == "OK"
        and support_status == "OK"
        and not baseline_mismatches
        and not data_incomplete
        and not support_problems
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "count_query_status": status,
        "dependencies": dependencies,
        "database_counts": database_counts,
        "manifest_loaded_counts": {name: expected_counts.get(name) for name in dependencies},
        "baseline_mismatches": baseline_mismatches,
        "data_incomplete": data_incomplete,
        "update_support_counts": support_counts,
        "update_support_problems": support_problems,
        "raw_output_sha256": hashlib.sha256(
            (output + support_output).encode("utf-8")
        ).hexdigest(),
    }


def baseline_manifest_mismatches(
    baseline_counts: Dict[str, int],
    manifest_rows: Sequence[Dict[str, object]],
) -> List[str]:
    expected_counts = manifest_loaded_counts(manifest_rows)
    mismatches = []
    for class_name, actual in baseline_counts.items():
        expected = expected_counts.get(class_name)
        if expected is None:
            mismatches.append(f"{class_name}:missing_manifest")
        elif actual != expected:
            mismatches.append(f"{class_name}:database={actual},manifest={expected}")
    return mismatches


def update_input_problems(
    filename: str,
    manifest_rows: Sequence[Dict[str, object]],
) -> List[str]:
    scopes = UPDATE_TARGET_SCOPES.get(filename, [])
    required_staging = sorted({staging_class for _label, staging_class, _sql in scopes})
    manifest = {
        str(row.get("class_name", "")): row
        for row in manifest_rows
        if row.get("class_name")
    }
    problems: List[str] = []
    for class_name in required_staging:
        row = manifest.get(class_name)
        if row is None:
            problems.append(f"{class_name}:missing_manifest")
            continue
        if str(row.get("status", "")) != "DONE":
            problems.append(f"{class_name}:status={row.get('status', '')}")
        if str(row.get("loader_mode", "")) != "derived_update_snapshot_v1":
            problems.append(f"{class_name}:loader_mode={row.get('loader_mode', '')}")
        if not is_true(row.get("source_rows_verified", "")):
            problems.append(f"{class_name}:source_rows_not_verified")
        if not is_true(row.get("source_current_match", "")):
            problems.append(f"{class_name}:source_fingerprint_mismatch")
        try:
            source_rows = int(str(row.get("source_rows", "0") or "0"))
            loaded_rows = int(str(row.get("loaded_rows", "0") or "0"))
            skipped_rows = int(str(row.get("skipped_rows", "0") or "0"))
        except ValueError:
            problems.append(f"{class_name}:invalid_manifest_counts")
            continue
        if source_rows != loaded_rows or skipped_rows != 0:
            problems.append(
                f"{class_name}:source={source_rows},loaded={loaded_rows},skipped={skipped_rows}"
            )
    return problems


def read_update_scope_counts(
    session: OrientDBConsoleSession,
    filename: str,
    timeout_s: int,
) -> Tuple[str, Dict[str, int], str]:
    counts: Dict[str, int] = {}
    outputs: List[str] = []
    for label, _staging_class, statement in UPDATE_TARGET_SCOPES.get(filename, []):
        result = session.run_statements([statement], timeout_s=timeout_s, measure_resources=False)
        outputs.append(result.output)
        value = scalar_from_result(result)
        if result.status != "OK" or value is None:
            return result.status, counts, "".join(outputs)
        counts[label] = value
    return "OK", counts, "".join(outputs)


def read_update_staging_counts(
    session: OrientDBConsoleSession,
    filename: str,
    timeout_s: int,
) -> Tuple[str, Dict[str, int], str]:
    classes = sorted(
        {staging_class for _label, staging_class, _statement in UPDATE_TARGET_SCOPES.get(filename, [])}
    )
    if not classes:
        return "ERROR", {}, "missing Update target scopes"
    return read_class_counts_batched(session, classes, timeout_s)


def read_update_support_counts(
    session: OrientDBConsoleSession,
    filename: str,
    timeout_s: int,
) -> Tuple[str, Dict[str, int], str]:
    classes = UPDATE_SUPPORT_CLASSES.get(filename, [])
    if not classes:
        return "OK", {}, ""
    return read_class_counts_batched(session, classes, timeout_s)


def validate_update_snapshot(
    filename: str,
    staging_counts: Dict[str, int],
) -> Tuple[bool, str]:
    required_staging = set(UPDATE_CLASS_STAGING.get(filename, {}).values())
    missing = sorted(required_staging - set(staging_counts))
    if missing:
        return False, "missing_staging_counts:" + ";".join(missing)
    if not staging_counts or not any(value > 0 for value in staging_counts.values()):
        return False, "target_snapshot_is_empty"
    return True, "derived_staging_snapshot_is_nonempty"


def validate_update_postcondition(
    filename: str,
    baseline_counts: Dict[str, int],
    post_counts: Dict[str, int],
    baseline_scope_counts: Dict[str, int],
    post_scope_counts: Dict[str, int],
    staging_counts: Dict[str, int],
) -> Tuple[bool, str]:
    if filename.endswith("b.sql"):
        class_differences = [
            f"{class_name}:baseline={baseline_counts[class_name]},post={post_counts.get(class_name)}"
            for class_name in baseline_counts
            if post_counts.get(class_name) != baseline_counts[class_name]
        ]
        if class_differences:
            return False, "restore_state_mismatch:" + ";".join(class_differences)
        support_differences = [
            f"{class_name}:baseline={baseline_scope_counts[class_name]},post={post_scope_counts.get(class_name)}"
            for class_name in baseline_scope_counts
            if post_scope_counts.get(class_name) != baseline_scope_counts[class_name]
        ]
        if support_differences:
            return False, "restore_support_state_mismatch:" + ";".join(support_differences)
        return True, "restored_affected_class_and_support_counts"

    class_differences = []
    for class_name, baseline in baseline_counts.items():
        staging_class = UPDATE_CLASS_STAGING[filename].get(class_name)
        expected = baseline if staging_class is None else baseline - staging_counts[staging_class]
        actual = post_counts.get(class_name)
        if actual != expected:
            class_differences.append(
                f"{class_name}:expected={expected},post={actual},staging={staging_class or 'UNCHANGED'}"
            )
    if class_differences:
        return False, "delete_class_delta_mismatch:" + ";".join(class_differences)
    support_differences = []
    for class_name, baseline in baseline_scope_counts.items():
        expected = baseline
        if filename == "6a.sql" and class_name == UPDATE6_AUTHOR_SHADOW:
            expected += staging_counts["grbench_update4_authors_gender"]
        actual = post_scope_counts.get(class_name)
        if actual != expected:
            support_differences.append(
                f"{class_name}:expected={expected},post={actual}"
            )
    if support_differences:
        return False, "delete_support_state_mismatch:" + ";".join(support_differences)
    return True, "deleted_exact_staging_cardinality_with_preserved_classes"


def validate_restore_endpoint_contract(filename: str, sql: str) -> Tuple[bool, str]:
    if filename not in {"2b.sql", "3b.sql", "5b.sql", "6b.sql"}:
        return True, "not_edge_restore"
    endpoint_selects = re.findall(
        r"LET\s+(?:from|to)_vertex\s*=\s*\((SELECT\s+FROM\s+[^;]+)\);",
        sql,
        flags=re.IGNORECASE,
    )
    if not endpoint_selects:
        return False, "missing_endpoint_selects"
    without_limit = [statement for statement in endpoint_selects if not re.search(r"\bLIMIT\s+1\b", statement, re.IGNORECASE)]
    if without_limit:
        return False, "endpoint_select_without_limit_1"
    placeholder_selects = [statement for statement in endpoint_selects if "_MissingEndpoint" in statement]
    if any("ifnull(" not in statement.lower() for statement in placeholder_selects):
        return False, "placeholder_select_without_null_normalization"
    return True, "single_endpoint_per_staging_row"


UPDATE_RESULT_COLUMNS = (
    "benchmark_value",
    "visited_rows",
    "missing_rows",
    "committed_batches",
)


def native_update_result_values(result: QueryRunResult) -> Dict[str, Optional[int]]:
    return {column: scalar_from_result(result, column) for column in UPDATE_RESULT_COLUMNS}


def validate_native_update_result(
    filename: str,
    result: QueryRunResult,
    staging_counts: Dict[str, int],
    batch_size: int,
) -> Tuple[bool, str, Dict[str, Optional[int]]]:
    values = native_update_result_values(result)
    if result.status != "OK":
        return False, f"worker_status_{result.status.lower()}", values
    missing_columns = [name for name, value in values.items() if value is None]
    if missing_columns:
        return False, "missing_worker_columns:" + ";".join(missing_columns), values

    staging_classes = list(UPDATE_CLASS_STAGING[filename].values())
    expected_rows = sum(staging_counts[class_name] for class_name in staging_classes)
    expected_batches = sum(
        (staging_counts[class_name] + batch_size - 1) // batch_size
        for class_name in staging_classes
        if staging_counts[class_name] > 0
    )
    problems = []
    if values["benchmark_value"] != expected_rows:
        problems.append(
            f"modified_rows={values['benchmark_value']},expected={expected_rows}"
        )
    if values["visited_rows"] != expected_rows:
        problems.append(f"visited_rows={values['visited_rows']},expected={expected_rows}")
    if values["missing_rows"] != 0:
        problems.append(f"missing_rows={values['missing_rows']},expected=0")
    if values["committed_batches"] != expected_batches:
        problems.append(
            f"committed_batches={values['committed_batches']},expected={expected_batches}"
        )
    if problems:
        return False, "native_worker_contract_mismatch:" + ";".join(problems), values
    return True, "native_worker_counts_match_staging", values


def support_counts_match_without_recovery_progress(
    expected: Dict[str, int],
    actual: Dict[str, int],
) -> bool:
    return all(
        actual.get(class_name) == expected_count
        for class_name, expected_count in expected.items()
        if class_name != UPDATE_RECOVERY_PROGRESS
    )


def recovery_business_state_is_baseline(
    baseline_counts: Dict[str, int],
    current_counts: Optional[Dict[str, int]],
    baseline_support_counts: Dict[str, int],
    current_support_status: str,
    current_support_counts: Dict[str, int],
) -> bool:
    return (
        current_counts == baseline_counts
        and current_support_status == "OK"
        and support_counts_match_without_recovery_progress(
            baseline_support_counts,
            current_support_counts,
        )
    )


def finalize_and_verify_recovery_progress(
    session: OrientDBConsoleSession,
    filename: str,
    batch_size: int,
    baseline_counts: Dict[str, int],
    baseline_support_counts: Dict[str, int],
    timeout_s: int,
) -> Tuple[bool, str, str, bool]:
    outputs: List[str] = []
    finalized = session.run_update(
        filename=filename,
        batch_size=batch_size,
        mode="FINALIZE_RECOVERY",
        timeout_s=timeout_s,
        measure_resources=False,
    )
    outputs.append(
        f"--- RECOVERY PROGRESS FINALIZE status={finalized.status} "
        f"elapsed={finalized.elapsed:.6f}s ---\n{finalized.output}"
    )
    if finalized.status != "OK":
        return (
            False,
            f"recovery_progress_finalize_{finalized.status.lower()}",
            "".join(outputs),
            finalized.status in {"TIMEOUT", "CRASHED"},
        )

    count_result, final_counts = read_class_counts(
        session,
        list(baseline_counts),
        timeout_s,
    )
    support_status, final_support_counts, support_output = read_update_support_counts(
        session,
        filename,
        timeout_s,
    )
    outputs.append(
        f"--- RECOVERY PROGRESS FINALIZE BASELINE status={count_result.status} ---\n"
        f"{count_result.output}"
        f"--- RECOVERY PROGRESS FINALIZE SUPPORT status={support_status} ---\n"
        f"{support_output}"
    )
    if final_counts == baseline_counts and final_support_counts == baseline_support_counts:
        return True, "baseline_verified_and_recovery_progress_cleared", "".join(outputs), False
    restart_required = (
        count_result.status in {"TIMEOUT", "CRASHED"}
        or support_status in {"TIMEOUT", "CRASHED"}
    )
    return (
        False,
        "post_finalize_baseline_mismatch:"
        f"classes={final_counts},support={final_support_counts},support_status={support_status}",
        "".join(outputs),
        restart_required,
    )


def recover_and_verify_update_baseline(
    session: OrientDBConsoleSession,
    filename: str,
    batch_size: int,
    baseline_counts: Dict[str, int],
    baseline_support_counts: Dict[str, int],
    staging_counts: Dict[str, int],
    timeout_s: int,
    process_lost: bool,
    max_attempts: int = 2,
) -> Tuple[bool, str, str]:
    outputs: List[str] = []
    restart_required = process_lost
    last_note = "recovery_not_started"
    force_normalize = False
    for attempt in range(1, max_attempts + 1):
        if restart_required:
            try:
                session.restart()
            except Exception as exc:
                return False, f"recovery_restart_failed:{exc}", "".join(outputs)
            restart_required = False
        current_result, current_counts = read_class_counts(
            session,
            list(baseline_counts),
            timeout_s,
        )
        current_support_status, current_support_counts, current_support_output = (
            read_update_support_counts(session, filename, timeout_s)
        )
        outputs.append(
            f"--- RECOVER ATTEMPT {attempt} CURRENT STATE status={current_result.status} ---\n"
            f"{current_result.output}"
            f"--- RECOVER ATTEMPT {attempt} CURRENT SUPPORT "
            f"status={current_support_status} ---\n{current_support_output}"
        )

        business_state_is_baseline = recovery_business_state_is_baseline(
            baseline_counts,
            current_counts,
            baseline_support_counts,
            current_support_status,
            current_support_counts,
        )
        progress_count = current_support_counts.get(UPDATE_RECOVERY_PROGRESS, 0)
        if business_state_is_baseline and progress_count == 0:
            return (
                True,
                f"baseline_and_support_counts_already_restored_on_attempt_{attempt}",
                "".join(outputs),
            )
        if business_state_is_baseline and progress_count > 0:
            finalized, finalize_note, finalize_output, finalize_restart = (
                finalize_and_verify_recovery_progress(
                    session,
                    filename,
                    batch_size,
                    baseline_counts,
                    baseline_support_counts,
                    timeout_s,
                )
            )
            outputs.append(finalize_output)
            if finalized:
                return True, f"{finalize_note}_on_attempt_{attempt}", "".join(outputs)
            last_note = f"attempt_{attempt}_{finalize_note}"
            restart_required = finalize_restart
            force_normalize = True
            continue

        delete_state_valid = False
        delete_state_note = "current_state_unavailable"
        if (
            current_counts is not None
            and current_support_status == "OK"
        ):
            delete_state_valid, delete_state_note = validate_update_postcondition(
                UPDATE_SETUP_FILES.get(filename, filename),
                baseline_counts,
                current_counts,
                baseline_support_counts,
                current_support_counts,
                staging_counts,
            )
        if progress_count > 0 and not force_normalize:
            recovery_mode = "RESTORE_ONLY"
            recovery_reason = f"recovery_progress_rows={progress_count}"
        elif delete_state_valid and not force_normalize:
            recovery_mode = "RESTORE_ONLY"
            recovery_reason = delete_state_note
        else:
            recovery_mode = "RECOVER"
            recovery_reason = (
                f"forced_normalization_after_failed_resume:{delete_state_note}"
                if force_normalize
                else delete_state_note
            )
        outputs.append(
            f"--- RECOVER ATTEMPT {attempt} STRATEGY mode={recovery_mode} "
            f"reason={recovery_reason} ---\n"
        )
        recovery = session.run_update(
            filename=filename,
            batch_size=batch_size,
            mode=recovery_mode,
            timeout_s=timeout_s,
            measure_resources=False,
        )
        outputs.append(
            f"--- RECOVER ATTEMPT {attempt} status={recovery.status} "
            f"elapsed={recovery.elapsed:.6f}s ---\n{recovery.output}"
        )
        if recovery.status != "OK":
            last_note = f"recover_attempt_{attempt}_{recovery.status.lower()}"
            restart_required = recovery.status in {"TIMEOUT", "CRASHED"}
            if recovery_mode == "RECOVER":
                force_normalize = False
            continue

        count_result, restored_counts = read_class_counts(
            session,
            list(baseline_counts),
            timeout_s,
        )
        support_status, restored_support_counts, support_output = read_update_support_counts(
            session,
            filename,
            timeout_s,
        )
        outputs.append(
            f"--- RECOVER ATTEMPT {attempt} BASELINE status={count_result.status} ---\n"
            f"{count_result.output}"
            f"--- RECOVER ATTEMPT {attempt} SUPPORT BASELINE status={support_status} ---\n"
            f"{support_output}"
        )
        if recovery_business_state_is_baseline(
            baseline_counts,
            restored_counts,
            baseline_support_counts,
            support_status,
            restored_support_counts,
        ):
            restored_progress_count = restored_support_counts.get(
                UPDATE_RECOVERY_PROGRESS,
                0,
            )
            if restored_progress_count > 0:
                finalized, finalize_note, finalize_output, finalize_restart = (
                    finalize_and_verify_recovery_progress(
                        session,
                        filename,
                        batch_size,
                        baseline_counts,
                        baseline_support_counts,
                        timeout_s,
                    )
                )
                outputs.append(finalize_output)
                if finalized:
                    return True, f"{finalize_note}_on_attempt_{attempt}", "".join(outputs)
                last_note = f"recover_attempt_{attempt}_{finalize_note}"
                restart_required = finalize_restart
                force_normalize = True
                continue
            if restored_support_counts == baseline_support_counts:
                return (
                    True,
                    f"baseline_and_support_counts_restored_on_attempt_{attempt}",
                    "".join(outputs),
                )
        if restored_counts is None:
            last_note = f"recover_attempt_{attempt}_recount_{count_result.status.lower()}"
            restart_required = count_result.status in {"TIMEOUT", "CRASHED"}
        else:
            last_note = (
                f"recover_attempt_{attempt}_baseline_count_mismatch:"
                f"classes={restored_counts},support={restored_support_counts},"
                f"support_status={support_status}"
            )
            restart_required = support_status in {"TIMEOUT", "CRASHED"}
        if recovery_mode == "RESTORE_ONLY" and recovery.status == "OK":
            force_normalize = True
    return False, last_note, "".join(outputs)


def empty_run_result(status: str, output: str = "") -> QueryRunResult:
    return QueryRunResult(status=status, elapsed=0.0, metrics=Metrics(), output=output)


def run_update_query_file_warm(
    sf: str,
    query: QuerySpec,
    session: OrientDBConsoleSession,
    log_dir: Path,
    timeout_s: int,
    setup_timeout_s: int,
    recovery_timeout_s: int,
    recovery_max_attempts: int,
    update_batch_size: int,
    success_status: str,
    runs: int,
    warmup_runs: int,
    manifest_rows: Sequence[Dict[str, object]],
    source_query_root: Path = DEFAULT_SOURCE_QUERY_ROOT,
) -> Dict[str, object]:
    filename = query.path.name
    affected_classes = UPDATE_AFFECTED_CLASSES.get(filename)
    if not affected_classes:
        raise RuntimeError(f"missing strict Update contract for {query.rel_path}")

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / safe_log_name(query.rel_path)
    input_problems = update_input_problems(filename, manifest_rows)
    endpoint_contract_valid, endpoint_contract_note = validate_restore_endpoint_contract(
        filename, query.sql
    )
    if not endpoint_contract_valid:
        input_problems.append(endpoint_contract_note)
    if input_problems:
        message = "Update staging provenance failed: " + ";".join(input_problems)
        log_path.write_text(message + "\n", errors="replace")
        row = row_from_result(
            sf=sf,
            query=query,
            status="UPDATE_INPUT_INVALID",
            output=message,
            elapsed=0.0,
            metrics=Metrics(),
            log_rel=result_path_reference(log_path),
            runs=0,
            run_elapsed_sec=[],
            source_query_root=source_query_root,
        )
        row.update(
            {
                "update_isolation": "not_started_invalid_input",
                "setup_in_timed_window": False,
                "setup_status": "NOT_STARTED",
                "setup_elapsed_sec": "[]",
                "update_input_status": "FAIL",
                "update_input_problems": json.dumps(input_problems),
                "update_validation_status": "FAIL",
                "update_validation_notes": json.dumps([message]),
                "baseline_counts": "[]",
                "baseline_scope_counts": "[]",
                "staging_counts": "[]",
                "post_counts": "[]",
                "post_scope_counts": "[]",
                "baseline_restored": True,
                "update_nontrivial": False,
                "update_comparability_class": UPDATE_COMPARABILITY_CLASS.get(
                    filename, "CONTRACT_ALIGNED"
                ),
                "warmup_runs_requested": warmup_runs,
                "warmup_runs_completed": 0,
                "warmup_status": "FAIL",
                "update_batch_size": update_batch_size,
                "update_recovery_timeout_seconds": recovery_timeout_s,
                "update_recovery_max_attempts": recovery_max_attempts,
                "update_worker_protocol": UPDATE_WORKER_PROTOCOL,
                "update_worker_diagnostics": "[]",
                "compensation_statuses": "[]",
                "compensation_elapsed_sec": "[]",
                "emergency_recovery_used": False,
                "emergency_recovery_succeeded": True,
            }
        )
        return row

    log_parts: List[str] = []
    measured_results: List[QueryRunResult] = []
    terminal_result: Optional[QueryRunResult] = None
    warmup_completed = 0
    setup_elapsed: List[float] = []
    validation_notes: List[str] = []
    baseline_snapshots: List[Dict[str, int]] = []
    baseline_scope_snapshots: List[Dict[str, int]] = []
    staging_snapshots: List[Dict[str, int]] = []
    post_snapshots: List[Dict[str, int]] = []
    post_scope_snapshots: List[Dict[str, int]] = []
    final_baseline_snapshots: List[Dict[str, int]] = []
    final_support_snapshots: List[Dict[str, int]] = []
    setup_statuses: List[str] = []
    compensation_statuses: List[str] = []
    compensation_elapsed: List[float] = []
    recovery_notes: List[str] = []
    worker_diagnostics: List[Dict[str, object]] = []
    overall_status = success_status
    baseline_restored = True
    update_nontrivial = False
    setup_status = "NOT_REQUIRED" if filename.endswith("a.sql") else "PENDING"
    emergency_recovery_used = False
    emergency_recovery_succeeded = True

    for iteration_index in range(warmup_runs + runs):
        is_warmup = iteration_index < warmup_runs
        phase = "WARMUP" if is_warmup else "RUN"
        phase_index = iteration_index + 1 if is_warmup else iteration_index - warmup_runs + 1
        log_parts.append(f"--- {phase} {phase_index} BASELINE ---\n")
        baseline_result, baseline_counts = read_class_counts(session, affected_classes, setup_timeout_s)
        log_parts.append(baseline_result.output)
        if baseline_counts is None:
            terminal_result = empty_run_result("BASELINE_CHECK_FAILED", baseline_result.output)
            overall_status = "BASELINE_CHECK_FAILED"
            baseline_restored = False
            break
        baseline_snapshots.append(baseline_counts)
        manifest_mismatches = baseline_manifest_mismatches(baseline_counts, manifest_rows)
        if manifest_mismatches:
            message = "baseline differs from loader manifest: " + ";".join(manifest_mismatches)
            terminal_result = empty_run_result("BASELINE_MISMATCH", message)
            validation_notes.append(message)
            overall_status = "BASELINE_MISMATCH"
            break

        support_status, baseline_scope_counts, support_output = read_update_support_counts(
            session,
            filename,
            setup_timeout_s,
        )
        log_parts.append(
            f"--- {phase} {phase_index} SUPPORT BASELINE status={support_status} ---\n"
            f"{support_output}"
        )
        if support_status != "OK" or any(baseline_scope_counts.values()):
            message = (
                f"Update support baseline invalid: status={support_status},"
                f"counts={baseline_scope_counts}"
            )
            terminal_result = empty_run_result("BASELINE_MISMATCH", message)
            validation_notes.append(message)
            overall_status = "BASELINE_MISMATCH"
            baseline_restored = False
            break
        baseline_scope_snapshots.append(baseline_scope_counts)

        staging_status, staging_counts, staging_output = read_update_staging_counts(
            session, filename, setup_timeout_s
        )
        log_parts.append(f"--- {phase} {phase_index} STAGING COUNTS ---\n{staging_output}")
        if staging_status != "OK":
            message = f"staging count failed: status={staging_status}"
            terminal_result = empty_run_result("BASELINE_CHECK_FAILED", message)
            validation_notes.append(message)
            overall_status = "BASELINE_CHECK_FAILED"
            baseline_restored = False
            break
        staging_snapshots.append(staging_counts)
        snapshot_valid, snapshot_note = validate_update_snapshot(filename, staging_counts)
        validation_notes.append(f"baseline:{snapshot_note}")
        if not snapshot_valid:
            terminal_result = empty_run_result("BASELINE_MISMATCH", snapshot_note)
            overall_status = "BASELINE_MISMATCH"
            break
        update_nontrivial = True

        setup_failed = False
        setup_failure_note = ""
        if filename in UPDATE_SETUP_FILES:
            setup_filename = UPDATE_SETUP_FILES[filename]
            setup = session.run_update(
                filename=setup_filename,
                batch_size=update_batch_size,
                mode="STRICT",
                timeout_s=setup_timeout_s,
                measure_resources=False,
            )
            setup_elapsed.append(setup.elapsed)
            setup_status = setup.status
            setup_statuses.append(setup.status)
            log_parts.append(
                f"--- {phase} {phase_index} SETUP {setup_filename} "
                f"status={setup.status} elapsed={setup.elapsed:.6f}s ---\n{setup.output}"
            )
            if setup.status == "OK":
                setup_worker_valid, setup_worker_note, setup_values = validate_native_update_result(
                    setup_filename,
                    setup,
                    staging_counts,
                    update_batch_size,
                )
                worker_diagnostics.append(
                    {
                        "phase": phase,
                        "iteration": phase_index,
                        "role": "setup",
                        "file": setup_filename,
                        "status": setup.status,
                        "validation": setup_worker_note,
                        **setup_values,
                    }
                )
                validation_notes.append(f"setup_worker:{setup_worker_note}")
                if not setup_worker_valid:
                    setup_failed = True
                    setup_failure_note = setup_worker_note
                setup_count_result, setup_counts = read_class_counts(session, affected_classes, setup_timeout_s)
                log_parts.append(setup_count_result.output)
                if setup_counts is None:
                    setup_status = "VALIDATION_ERROR"
                    setup_failed = True
                    setup_failure_note = f"setup_count_{setup_count_result.status.lower()}"
                else:
                    setup_support_status, setup_support_counts, setup_support_output = (
                        read_update_support_counts(
                            session,
                            setup_filename,
                            setup_timeout_s,
                        )
                    )
                    log_parts.append(setup_support_output)
                    setup_valid, setup_note = validate_update_postcondition(
                        setup_filename,
                        baseline_counts,
                        setup_counts,
                        baseline_scope_counts,
                        setup_support_counts,
                        staging_counts,
                    )
                    if setup_support_status != "OK":
                        setup_valid = False
                        setup_note = f"setup_support_count_{setup_support_status.lower()}"
                    validation_notes.append(f"setup:{setup_note}")
                    if not setup_valid:
                        setup_status = "VALIDATION_FAILED"
                        setup_failed = True
                        setup_failure_note = setup_note
            else:
                setup_failed = True
                setup_failure_note = f"setup_worker_status_{setup.status.lower()}"
                worker_diagnostics.append(
                    {
                        "phase": phase,
                        "iteration": phase_index,
                        "role": "setup",
                        "file": setup_filename,
                        "status": setup.status,
                        **native_update_result_values(setup),
                    }
                )

            if setup_failed:
                process_lost = setup.status in {"TIMEOUT", "CRASHED"}
                emergency_recovery_used = True
                restored, restore_note, restore_output = recover_and_verify_update_baseline(
                    session,
                    filename,
                    update_batch_size,
                    baseline_counts,
                    baseline_scope_counts,
                    staging_counts,
                    recovery_timeout_s,
                    process_lost,
                    max_attempts=recovery_max_attempts,
                )
                recovery_notes.append(f"setup:{restore_note}")
                log_parts.append(
                    f"--- {phase} {phase_index} SETUP RECOVERY {restore_note} ---\n"
                    f"{restore_output}"
                )
                baseline_restored = restored
                emergency_recovery_succeeded = emergency_recovery_succeeded and restored
                terminal_result = empty_run_result(
                    "DEPENDENCY_FAILED",
                    f"{setup_failure_note}\n{setup.output}",
                )
                overall_status = "DEPENDENCY_FAILED" if restored else "BASELINE_CORRUPTED"
                break

        measured = session.run_update(
            filename=filename,
            batch_size=update_batch_size,
            mode="STRICT",
            timeout_s=timeout_s,
            measure_resources=not is_warmup,
        )
        terminal_result = measured
        if not is_warmup:
            measured_results.append(measured)
        log_parts.append(
            f"--- {phase} {phase_index} SUBJECT status={measured.status} "
            f"elapsed={measured.elapsed:.6f}s ---\n{measured.output}"
        )

        measured_worker_valid = False
        measured_worker_note = f"worker_status_{measured.status.lower()}"
        measured_values = native_update_result_values(measured)
        if measured.status == "OK":
            measured_worker_valid, measured_worker_note, measured_values = validate_native_update_result(
                filename,
                measured,
                staging_counts,
                update_batch_size,
            )
        worker_diagnostics.append(
            {
                "phase": phase,
                "iteration": phase_index,
                "role": "subject",
                "file": filename,
                "status": measured.status,
                "validation": measured_worker_note,
                **measured_values,
            }
        )
        validation_notes.append(f"measured_worker:{measured_worker_note}")

        post_valid = False
        post_note = measured_worker_note
        if measured.status == "OK" and measured_worker_valid:
            post_count_result, post_counts = read_class_counts(session, affected_classes, setup_timeout_s)
            log_parts.append(post_count_result.output)
            if post_counts is not None:
                post_snapshots.append(post_counts)
                post_support_status, post_scope_counts, post_support_output = (
                    read_update_support_counts(
                        session,
                        filename,
                        setup_timeout_s,
                    )
                )
                log_parts.append(post_support_output)
                post_scope_snapshots.append(post_scope_counts)
                if filename.endswith("b.sql"):
                    post_valid, post_note = validate_update_postcondition(
                        filename,
                        baseline_counts,
                        post_counts,
                        baseline_scope_counts,
                        post_scope_counts,
                        staging_counts,
                    )
                    validation_notes.append(
                        f"measured:{post_note};{endpoint_contract_note};"
                        "derived_staging_cardinality_contract"
                    )
                else:
                    post_valid, post_note = validate_update_postcondition(
                        filename,
                        baseline_counts,
                        post_counts,
                        baseline_scope_counts,
                        post_scope_counts,
                        staging_counts,
                    )
                    validation_notes.append(f"measured:{post_note}")
                if post_support_status != "OK":
                    post_valid = False
                    post_note = f"post_support_count_{post_support_status.lower()}"
                    validation_notes.append(f"measured:{post_note}")
            else:
                post_note = f"post_count_{post_count_result.status.lower()}"
                validation_notes.append(f"measured:{post_note}")

        if measured.status != "OK" or not measured_worker_valid or not post_valid:
            process_lost = measured.status in {"TIMEOUT", "CRASHED"}
            emergency_recovery_used = True
            restored, restore_note, restore_output = recover_and_verify_update_baseline(
                session,
                filename,
                update_batch_size,
                baseline_counts,
                baseline_scope_counts,
                staging_counts,
                recovery_timeout_s,
                process_lost,
                max_attempts=recovery_max_attempts,
            )
            recovery_notes.append(f"subject:{restore_note}")
            log_parts.append(
                f"--- {phase} {phase_index} SUBJECT RECOVERY {restore_note} ---\n"
                f"{restore_output}"
            )
            baseline_restored = baseline_restored and restored
            emergency_recovery_succeeded = emergency_recovery_succeeded and restored
            if not restored:
                overall_status = "BASELINE_CORRUPTED"
            elif measured.status != "OK":
                overall_status = measured.status
            else:
                overall_status = "VALIDATION_FAILED"
            break

        if filename.endswith("a.sql"):
            compensation_filename = filename.replace("a.sql", "b.sql")
            compensation = session.run_update(
                filename=compensation_filename,
                batch_size=update_batch_size,
                mode="STRICT",
                timeout_s=setup_timeout_s,
                measure_resources=False,
            )
            compensation_elapsed.append(compensation.elapsed)
            compensation_statuses.append(compensation.status)
            compensation_valid = False
            compensation_note = f"worker_status_{compensation.status.lower()}"
            compensation_values = native_update_result_values(compensation)
            if compensation.status == "OK":
                compensation_valid, compensation_note, compensation_values = validate_native_update_result(
                    compensation_filename,
                    compensation,
                    staging_counts,
                    update_batch_size,
                )
            worker_diagnostics.append(
                {
                    "phase": phase,
                    "iteration": phase_index,
                    "role": "compensation",
                    "file": compensation_filename,
                    "status": compensation.status,
                    "validation": compensation_note,
                    **compensation_values,
                }
            )
            validation_notes.append(f"compensation:{compensation_note}")
            log_parts.append(
                f"--- {phase} {phase_index} COMPENSATION {compensation_filename} "
                f"status={compensation.status} elapsed={compensation.elapsed:.6f}s ---\n"
                f"{compensation.output}"
            )
            if not compensation_valid:
                emergency_recovery_used = True
                restored, restore_note, restore_output = recover_and_verify_update_baseline(
                    session,
                    filename,
                    update_batch_size,
                    baseline_counts,
                    baseline_scope_counts,
                    staging_counts,
                    recovery_timeout_s,
                    compensation.status in {"TIMEOUT", "CRASHED"},
                    max_attempts=recovery_max_attempts,
                )
                recovery_notes.append(f"compensation:{restore_note}")
                log_parts.append(
                    f"--- {phase} {phase_index} COMPENSATION RECOVERY {restore_note} ---\n"
                    f"{restore_output}"
                )
                baseline_restored = baseline_restored and restored
                emergency_recovery_succeeded = emergency_recovery_succeeded and restored
                overall_status = "VALIDATION_FAILED" if restored else "BASELINE_CORRUPTED"
                break

        final_count_result, final_counts = read_class_counts(
            session,
            affected_classes,
            setup_timeout_s,
        )
        log_parts.append(
            f"--- {phase} {phase_index} FINAL BASELINE status={final_count_result.status} ---\n"
            f"{final_count_result.output}"
        )
        final_support_status, final_support_counts, final_support_output = read_update_support_counts(
            session,
            filename,
            setup_timeout_s,
        )
        log_parts.append(
            f"--- {phase} {phase_index} FINAL SUPPORT BASELINE "
            f"status={final_support_status} ---\n{final_support_output}"
        )
        if (
            final_counts != baseline_counts
            or final_support_status != "OK"
            or final_support_counts != baseline_scope_counts
        ):
            emergency_recovery_used = True
            restored, restore_note, restore_output = recover_and_verify_update_baseline(
                session,
                filename,
                update_batch_size,
                baseline_counts,
                baseline_scope_counts,
                staging_counts,
                recovery_timeout_s,
                final_count_result.status in {"TIMEOUT", "CRASHED"}
                or final_support_status in {"TIMEOUT", "CRASHED"},
                max_attempts=recovery_max_attempts,
            )
            recovery_notes.append(f"final_baseline:{restore_note}")
            log_parts.append(
                f"--- {phase} {phase_index} FINAL BASELINE RECOVERY {restore_note} ---\n"
                f"{restore_output}"
            )
            baseline_restored = baseline_restored and restored
            emergency_recovery_succeeded = emergency_recovery_succeeded and restored
            validation_notes.append(
                f"final_baseline_mismatch:expected={baseline_counts},actual={final_counts},"
                f"support_expected={baseline_scope_counts},support_actual={final_support_counts}"
            )
            overall_status = "VALIDATION_FAILED" if restored else "BASELINE_CORRUPTED"
            break
        final_baseline_snapshots.append(final_counts)
        final_support_snapshots.append(final_support_counts)
        validation_notes.append("final:baseline_and_support_counts_restored")
        if is_warmup:
            warmup_completed += 1

    log_path.write_text("".join(log_parts), errors="replace")
    selected = (
        measured_results[median_run_index(measured_results)]
        if measured_results
        else terminal_result
        if terminal_result is not None
        else empty_run_result("ERROR", "no Update execution occurred")
    )
    if overall_status == success_status and (
        any(result.status != "OK" for result in measured_results)
        or len(measured_results) != runs
        or warmup_completed != warmup_runs
    ):
        overall_status = "ERROR"
    elapsed = timeout_s if overall_status == "TIMEOUT" else selected.elapsed
    row = row_from_result(
        sf=sf,
        query=query,
        status=overall_status,
        output=selected.output,
        elapsed=elapsed,
        metrics=selected.metrics,
        log_rel=result_path_reference(log_path),
        runs=len(measured_results),
        run_elapsed_sec=[result.elapsed for result in measured_results],
        result_sets=selected.result_sets,
        client_elapsed=selected.client_elapsed,
        run_client_elapsed_sec=[result.client_elapsed for result in measured_results],
        source_query_root=source_query_root,
    )
    row.update(
        {
            "update_isolation": UPDATE_ISOLATION_MODE,
            "update_batch_size": update_batch_size,
            "update_recovery_timeout_seconds": recovery_timeout_s,
            "update_recovery_max_attempts": recovery_max_attempts,
            "update_worker_protocol": UPDATE_WORKER_PROTOCOL,
            "update_worker_diagnostics": json.dumps(worker_diagnostics, sort_keys=True),
            "setup_in_timed_window": False,
            "setup_status": setup_status,
            "setup_statuses": json.dumps(setup_statuses),
            "setup_elapsed_sec": json.dumps([round(value, 6) for value in setup_elapsed]),
            "compensation_statuses": json.dumps(compensation_statuses),
            "compensation_elapsed_sec": json.dumps(
                [round(value, 6) for value in compensation_elapsed]
            ),
            "emergency_recovery_used": emergency_recovery_used,
            "emergency_recovery_succeeded": emergency_recovery_succeeded,
            "emergency_recovery_notes": json.dumps(recovery_notes, ensure_ascii=False),
            "update_input_status": "PASS",
            "update_input_problems": "[]",
            "update_validation_status": (
                "PASS"
                if overall_status == success_status
                and warmup_completed == warmup_runs
                and len(measured_results) == runs
                else "FAIL"
            ),
            "update_validation_notes": json.dumps(validation_notes, ensure_ascii=False),
            "baseline_counts": json.dumps(baseline_snapshots, sort_keys=True),
            "baseline_scope_counts": json.dumps(baseline_scope_snapshots, sort_keys=True),
            "staging_counts": json.dumps(staging_snapshots, sort_keys=True),
            "post_counts": json.dumps(post_snapshots, sort_keys=True),
            "post_scope_counts": json.dumps(post_scope_snapshots, sort_keys=True),
            "final_baseline_counts": json.dumps(final_baseline_snapshots, sort_keys=True),
            "final_support_counts": json.dumps(final_support_snapshots, sort_keys=True),
            "baseline_restored": baseline_restored,
            "update_nontrivial": update_nontrivial,
            "update_comparability_class": UPDATE_COMPARABILITY_CLASS.get(
                filename, "CONTRACT_ALIGNED"
            ),
            "warmup_runs_requested": warmup_runs,
            "warmup_runs_completed": warmup_completed,
            "warmup_status": "PASS" if warmup_completed == warmup_runs else "FAIL",
        }
    )
    return row


def run_query_file_cold(
    sf: str,
    query: QuerySpec,
    db_path: Path,
    orientdb_home: Path,
    java_home: Path,
    log_dir: Path,
    timeout_s: int,
    success_status: str,
    heap: str,
    sample_interval_s: float,
    source_query_root: Path = DEFAULT_SOURCE_QUERY_ROOT,
) -> Dict[str, object]:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / safe_log_name(query.rel_path)
    script = "\n".join(f"{statement};" for statement in query_statements(query))
    username, password = orientdb_credentials()
    console_input = (
        f"set maxWidth {CONSOLE_MAX_WIDTH}\n"
        f"connect plocal:{db_path} {username} {password}\n{script}\nexit\n"
    )

    env = console_env(orientdb_home, java_home, heap if success_status == "OK" else "")

    proc = subprocess.Popen(
        [str(orientdb_home / "bin" / "console.sh")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
        env=env,
    )
    monitor = ResourceMonitor(proc.pid, interval_s=sample_interval_s)
    start = time.monotonic()
    monitor.start()
    timed_out = False
    output = ""
    try:
        output, _ = proc.communicate(input=console_input, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_tree(proc.pid)
        try:
            output, _ = proc.communicate(timeout=5)
        except Exception:
            pass
    finally:
        metrics = monitor.stop()
    elapsed = time.monotonic() - start
    output = redact_orientdb_password(output, password)
    log_path.write_text(output, encoding="utf-8", errors="replace")
    if timed_out:
        status = "TIMEOUT"
    elif proc.returncode not in (0, None):
        status = "CRASHED"
    elif "!ERROR:" in output or "Exception" in output:
        status = "ERROR"
    else:
        status = success_status

    return row_from_result(
        sf=sf,
        query=query,
        status=status,
        output=output,
        elapsed=elapsed,
        metrics=metrics,
        log_rel=result_path_reference(log_path),
        runs=1,
        run_elapsed_sec=[elapsed],
        client_elapsed=elapsed,
        run_client_elapsed_sec=[elapsed],
        execution_backend="cold_console",
        source_query_root=source_query_root,
    )


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path) -> List[Dict[str, object]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


REUSED_UPDATE_BOOL_FIELDS = (
    "baseline_restored",
    "update_nontrivial",
    "emergency_recovery_used",
    "emergency_recovery_succeeded",
    "state_transition_match",
    "oracle_match",
    "oracle_source_match",
)


def load_reused_update_results(
    sources: Sequence[str],
    selected_sfs: Sequence[str],
    queries: Sequence[QuerySpec],
    source_query_root: Path,
    required_runs: int,
    required_warmup_runs: int,
    required_resource_sample_interval: float,
) -> Tuple[Dict[Tuple[str, str], Dict[str, object]], List[Dict[str, object]]]:
    update_queries = {
        query.rel_path: query for query in queries if query.category == "update"
    }
    selected_sf_set = set(selected_sfs)
    reused: Dict[Tuple[str, str], Dict[str, object]] = {}
    provenance: List[Dict[str, object]] = []
    for source in sources:
        source_path = Path(source).resolve()
        csv_path = source_path / "all_results.csv" if source_path.is_dir() else source_path
        result_dir = csv_path.parent
        metadata_path = result_dir / "metadata.json"
        if not csv_path.exists():
            raise SystemExit(f"reused Update result CSV not found: {csv_path}")
        if not metadata_path.exists():
            raise SystemExit(f"reused Update metadata not found: {metadata_path}")
        loaded_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(loaded_metadata, dict):
            raise SystemExit(f"reused Update metadata is not an object: {metadata_path}")
        metadata: Dict[str, object] = loaded_metadata
        metadata_problems: List[str] = []
        expected_metadata = {
            "benchmark_contract_version": BENCHMARK_CONTRACT_VERSION,
            "runs_per_query": required_runs,
            "warmup_runs_per_query": required_warmup_runs,
            "update_batch_size": DEFAULT_UPDATE_BATCH_SIZE,
            "update_worker_protocol": UPDATE_WORKER_PROTOCOL,
            "update_isolation": UPDATE_ISOLATION_MODE,
            "execution_mode": "warm",
            "execution_backend": "embedded_worker",
        }
        for field, expected in expected_metadata.items():
            if metadata.get(field) != expected:
                metadata_problems.append(
                    f"{field}={metadata.get(field)!r},required={expected!r}"
                )
        try:
            source_interval = float(metadata.get("resource_sampling_interval_seconds"))
        except (TypeError, ValueError):
            metadata_problems.append("invalid_resource_sampling_interval_seconds")
        else:
            if abs(source_interval - required_resource_sample_interval) > 1e-12:
                metadata_problems.append(
                    "resource_sampling_interval_seconds="
                    f"{source_interval},required={required_resource_sample_interval}"
                )
        if metadata_problems:
            raise SystemExit(
                f"reused Update metadata failed measurement-contract validation: {metadata_path}:"
                + ",".join(metadata_problems)
            )
        source_row_count = 0
        accepted_row_count = 0
        for raw_row in read_csv_rows(csv_path):
            source_row_count += 1
            if str(raw_row.get("category", "")) != "update":
                continue
            sf = str(raw_row.get("sf", ""))
            rel_path = str(raw_row.get("sql_file", ""))
            if sf not in selected_sf_set:
                continue
            query = update_queries.get(rel_path)
            if query is None:
                raise SystemExit(
                    f"reused Update row is not selected by the current query suite: {sf}:{rel_path}"
                )
            problems: List[str] = []
            if str(raw_row.get("benchmark_contract_version", "")) != BENCHMARK_CONTRACT_VERSION:
                problems.append("benchmark_contract_version_mismatch")
            if str(raw_row.get("update_worker_protocol", "")) != UPDATE_WORKER_PROTOCOL:
                problems.append("update_worker_protocol_mismatch")
            if str(raw_row.get("update_isolation", "")) != UPDATE_ISOLATION_MODE:
                problems.append("update_isolation_mismatch")
            try:
                if int(raw_row.get("update_batch_size", 0)) != DEFAULT_UPDATE_BATCH_SIZE:
                    problems.append("update_batch_size_mismatch")
            except (TypeError, ValueError):
                problems.append("invalid_update_batch_size")
            query_hash = hashlib.sha256(query.sql.encode("utf-8")).hexdigest()
            if str(raw_row.get("query_sql_sha256", "")) != query_hash:
                problems.append("query_sql_sha256_mismatch")
            source_sql_path = source_query_root / rel_path
            source_hash = (
                hashlib.sha256(source_sql_path.read_bytes()).hexdigest()
                if source_sql_path.exists()
                else ""
            )
            if str(raw_row.get("source_query_sql_sha256", "")) != source_hash:
                problems.append("source_query_sql_sha256_mismatch")
            status = str(raw_row.get("status", ""))
            if status not in {"OK", "TIMEOUT"}:
                problems.append(f"unsupported_status={status}")
            try:
                if int(raw_row.get("required_runs", -1)) != required_runs:
                    problems.append("required_runs_mismatch")
                if int(raw_row.get("required_warmup_runs", -1)) != required_warmup_runs:
                    problems.append("required_warmup_runs_mismatch")
            except (TypeError, ValueError):
                problems.append("invalid_row_measurement_contract")
            if str(raw_row.get("measurement_contract_status", "")) != "PASS":
                problems.append("measurement_contract_status_not_pass")
            if str(raw_row.get("update_input_status", "")) != "PASS":
                problems.append("update_input_status_not_pass")
            if not is_true(raw_row.get("baseline_restored", "")):
                problems.append("baseline_not_restored")
            if status == "OK":
                if str(raw_row.get("update_validation_status", "")) != "PASS":
                    problems.append("update_validation_status_not_pass")
                if not is_true(raw_row.get("update_nontrivial", "")):
                    problems.append("update_not_nontrivial")
            elif not is_true(raw_row.get("emergency_recovery_succeeded", "")):
                problems.append("timeout_recovery_not_proven")
            if problems:
                raise SystemExit(
                    f"reused Update row failed validation: {sf}:{rel_path}:"
                    + ",".join(problems)
                )
            key = (sf, rel_path)
            if key in reused:
                raise SystemExit(f"duplicate reused Update row: {sf}:{rel_path}")
            row: Dict[str, object] = dict(raw_row)
            for field in REUSED_UPDATE_BOOL_FIELDS:
                row[field] = is_true(row.get(field, ""))
            row["result_origin"] = "reused_update_acceptance"
            row["reused_result"] = True
            row["reused_result_dir"] = str(result_dir)
            row["reused_result_csv_sha256"] = file_sha256(csv_path)
            row["reused_original_required_runs"] = row.get("required_runs", "")
            row["reused_original_required_warmup_runs"] = row.get(
                "required_warmup_runs", ""
            )
            row["reused_original_measurement_contract_status"] = row.get(
                "measurement_contract_status", ""
            )
            row["reuse_validation_status"] = "PASS"
            reused[key] = row
            accepted_row_count += 1
        provenance.append(
            {
                "result_dir": str(result_dir),
                "csv_path": str(csv_path),
                "csv_sha256": file_sha256(csv_path),
                "metadata_path": str(metadata_path) if metadata_path.exists() else "",
                "benchmark_contract_version": metadata.get("benchmark_contract_version", ""),
                "runs_per_query": metadata.get("runs_per_query", ""),
                "warmup_runs_per_query": metadata.get("warmup_runs_per_query", ""),
                "resource_sampling_interval_seconds": metadata.get(
                    "resource_sampling_interval_seconds", ""
                ),
                "update_worker_protocol": metadata.get("update_worker_protocol", ""),
                "update_isolation": metadata.get("update_isolation", ""),
                "strict_execution_status": metadata.get("strict_execution_status", ""),
                "source_row_count": source_row_count,
                "accepted_update_row_count": accepted_row_count,
            }
        )
    return reused, provenance


def load_expected_results(path: str) -> Dict[str, object]:
    if not path:
        return {}
    expected_path = Path(path)
    if not expected_path.exists():
        raise SystemExit(f"expected-results manifest not found: {expected_path}")
    data = json.loads(expected_path.read_text())
    if not isinstance(data, dict):
        raise SystemExit("expected-results manifest must contain a JSON object")
    return data


def expected_result_entry(
    expected_results: Dict[str, object],
    sf: str,
    rel_path: str,
) -> Optional[Dict[str, object]]:
    root = expected_results.get("results", expected_results)
    if not isinstance(root, dict):
        return None
    direct = root.get(f"{sf}|{rel_path}")
    if isinstance(direct, dict):
        return direct
    sf_entries = root.get(sf)
    if isinstance(sf_entries, dict):
        entry = sf_entries.get(rel_path)
        if isinstance(entry, dict):
            return entry
    return None


def validate_expected_results(
    expected_results: Dict[str, object],
    queries: Sequence[QuerySpec],
    source_query_root: Path,
    selected_sfs: Sequence[str] = (),
) -> Dict[str, object]:
    read_queries = [query for query in queries if query.category != "update"]
    if not read_queries:
        return {"status": "NOT_REQUIRED", "problems": []}
    if not expected_results:
        return {"status": "MISSING", "problems": ["expected-results manifest was not supplied"]}
    problems: List[str] = []
    if expected_results.get("format_version") != ORACLE_FORMAT_VERSION:
        problems.append(
            f"format_version={expected_results.get('format_version', '<missing>')}"
            f",required={ORACLE_FORMAT_VERSION}"
        )
    oracle_errors = expected_results.get("errors", {})
    if not isinstance(oracle_errors, dict):
        problems.append("oracle errors must be an object")
    else:
        for sf in selected_sfs:
            sf_errors = oracle_errors.get(sf, {})
            if not isinstance(sf_errors, dict):
                problems.append(f"{sf}:oracle errors must be an object")
            elif sf_errors:
                problems.append(
                    f"{sf}:oracle contains {len(sf_errors)} generation error(s)"
                )
    expected_suite_hash = str(expected_results.get("source_query_suite_sha256", ""))
    actual_suite_hash = query_suite_sha256(read_queries, source_query_root)
    if expected_suite_hash != actual_suite_hash:
        problems.append(
            f"source_query_suite_sha256 mismatch: expected={expected_suite_hash or '<missing>'},"
            f"actual={actual_suite_hash}"
        )
    expected_query_suite_hash = str(expected_results.get("query_suite_sha256", ""))
    if expected_query_suite_hash != actual_suite_hash:
        problems.append(
            f"query_suite_sha256 mismatch: expected={expected_query_suite_hash or '<missing>'},"
            f"actual={actual_suite_hash}"
        )
    expected_count = expected_results.get("query_count")
    if expected_count is not None:
        try:
            if int(expected_count) != len(read_queries):
                problems.append(f"query_count mismatch: expected={expected_count},actual={len(read_queries)}")
        except (TypeError, ValueError):
            problems.append(f"invalid query_count={expected_count!r}")
    expected_paths = expected_results.get("query_paths")
    if expected_paths is not None:
        actual_paths = [query.rel_path for query in sorted(read_queries, key=lambda item: item.rel_path)]
        if expected_paths != actual_paths:
            problems.append("query_paths do not match the selected source query suite")
    root = expected_results.get("results", expected_results)
    def contains_alias(value: object) -> bool:
        if isinstance(value, dict):
            if "oracle_alias_of" in value:
                return True
            return any(contains_alias(item) for item in value.values())
        if isinstance(value, list):
            return any(contains_alias(item) for item in value)
        return False

    if contains_alias(root):
        problems.append("oracle_alias_of is forbidden; every query must be executed")
    for sf in selected_sfs:
        for query in read_queries:
            entry = expected_result_entry(expected_results, sf, query.rel_path)
            if entry is None:
                problems.append(f"{sf}:{query.rel_path}:missing oracle entry")
                continue
            expected_source_hash = hashlib.sha256(
                (source_query_root / query.rel_path).read_bytes()
            ).hexdigest()
            if entry.get("source_sql_sha256") != expected_source_hash:
                problems.append(f"{sf}:{query.rel_path}:source SQL hash mismatch")
            if not entry.get("result_values_sha256"):
                problems.append(f"{sf}:{query.rel_path}:missing result values hash")
            try:
                int(entry["result_row_count"])
            except (KeyError, TypeError, ValueError):
                problems.append(f"{sf}:{query.rel_path}:invalid result row count")
    if problems:
        return {"status": "FAIL", "problems": problems}
    return {"status": "PASS", "problems": []}


def query_data_integrity(
    query: QuerySpec,
    manifest_rows: Sequence[Dict[str, object]],
    require_source_provenance: bool = False,
) -> Tuple[str, List[str], List[str]]:
    manifest = {
        str(row.get("class_name", "")).lower(): row
        for row in manifest_rows
        if row.get("class_name")
    }
    dependencies = []
    problems = []
    for class_name, _parent in class_names_from_schema():
        if not re.search(rf"\b{re.escape(class_name)}\b", query.sql, flags=re.IGNORECASE):
            continue
        dependencies.append(class_name)
        row = manifest.get(class_name.lower())
        if row is None:
            problems.append(f"{class_name}:missing_manifest")
            continue
        status = str(row.get("status", ""))
        try:
            source_rows = int(str(row.get("source_rows", "0") or "0"))
            loaded_rows = int(str(row.get("loaded_rows", "0") or "0"))
            skipped_rows = int(str(row.get("skipped_rows", "0") or "0"))
        except ValueError:
            problems.append(f"{class_name}:invalid_manifest_counts")
            continue
        if status != "DONE":
            problems.append(f"{class_name}:status={status}")
        if skipped_rows != 0 or loaded_rows != source_rows:
            problems.append(
                f"{class_name}:source={source_rows},loaded={loaded_rows},skipped={skipped_rows}"
            )
        if require_source_provenance:
            if not is_true(row.get("source_rows_verified", "")):
                problems.append(f"{class_name}:source_rows_not_verified")
            if not is_true(row.get("source_current_match", "")):
                problems.append(f"{class_name}:source_fingerprint_mismatch")
    if problems:
        return "FAIL", dependencies, problems
    if not dependencies or not manifest_rows:
        return "UNKNOWN", dependencies, problems
    return "PASS", dependencies, problems


def annotate_result_validity(
    row: Dict[str, object],
    query: QuerySpec,
    manifest_rows: Sequence[Dict[str, object]],
    expected_results: Dict[str, object],
    required_runs: int,
    required_warmups: int,
    require_source_provenance: bool = False,
) -> None:
    data_status, dependencies, data_problems = query_data_integrity(
        query,
        manifest_rows,
        require_source_provenance=require_source_provenance,
    )
    row["data_integrity_status"] = data_status
    row["query_dependencies"] = json.dumps(dependencies)
    row["data_integrity_problems"] = json.dumps(data_problems)

    expected = expected_result_entry(expected_results, str(row["sf"]), query.rel_path)
    oracle_source_match = False
    if query.category == "update" and row.get("update_validation_status") == "PASS":
        correctness_status = "PASS_UPDATE_STATE_TRANSITION"
        oracle_match = False
        row["state_transition_match"] = True
    elif expected is None:
        correctness_status = "UNVERIFIED_NO_ORACLE"
        oracle_match = False
    else:
        expected_hash = str(expected.get("result_values_sha256", expected.get("result_sha256", "")))
        expected_rows = expected.get("result_row_count")
        expected_source_hash = str(expected.get("source_sql_sha256", ""))
        oracle_source_match = bool(expected_source_hash) and expected_source_hash == str(
            row.get("source_query_sql_sha256", "")
        )
        hash_matches = bool(expected_hash) and expected_hash == str(
            row.get("result_values_sha256", row.get("result_sha256", ""))
        )
        try:
            actual_rows = int(row.get("result_row_count", -1))
            rows_match = expected_rows is None or int(expected_rows) == actual_rows
        except (TypeError, ValueError):
            rows_match = False
        oracle_match = oracle_source_match and hash_matches and rows_match
        correctness_status = (
            "PASS"
            if oracle_match
            else "FAIL_ORACLE_SOURCE_MISMATCH"
            if not oracle_source_match
            else "FAIL_ORACLE_MISMATCH"
        )
        row["expected_result_values_sha256"] = expected_hash
        row["expected_result_row_count"] = "" if expected_rows is None else expected_rows
        row["expected_source_sql_sha256"] = expected_source_hash

    execution_ok = str(row.get("status")) in {"OK", "SCHEMA_ONLY_OK"}
    measurement_contract_ok = (
        str(row.get("execution_backend")) == "embedded_worker"
        and str(row.get("metric_window")) == "worker_pre_execute_to_fully_materialized_result"
        and int(row.get("runs", 0)) == required_runs
        and int(row.get("warmup_runs_completed", -1)) == required_warmups
        and str(row.get("warmup_status", "")) == "PASS"
    )
    update_ok = query.category != "update" or (
        row.get("update_input_status") == "PASS"
        and row.get("update_validation_status") == "PASS"
        and bool(row.get("baseline_restored"))
        and bool(row.get("update_nontrivial"))
        and row.get("update_comparability_class") == "CONTRACT_ALIGNED"
    )
    row["correctness_status"] = correctness_status
    row["oracle_match"] = oracle_match
    row["oracle_source_match"] = oracle_source_match
    row["required_runs"] = required_runs
    row["required_warmup_runs"] = required_warmups
    row["measurement_contract_status"] = "PASS" if measurement_contract_ok else "FAIL"
    row["comparison_eligible"] = bool(
        execution_ok
        and str(row.get("status")) == "OK"
        and data_status == "PASS"
        and correctness_status in {"PASS", "PASS_UPDATE_STATE_TRANSITION"}
        and update_ok
        and measurement_contract_ok
    )


def resumable_row(row: Dict[str, object]) -> bool:
    return (
        str(row.get("benchmark_contract_version", "")) == BENCHMARK_CONTRACT_VERSION
        and str(row.get("status", "")) == "OK"
        and str(row.get("data_integrity_status", "")) == "PASS"
        and str(row.get("correctness_status", "")) in {"PASS", "PASS_UPDATE_STATE_TRANSITION"}
        and str(row.get("measurement_contract_status", "")) == "PASS"
        and str(row.get("execution_backend", "")) == "embedded_worker"
        and str(row.get("comparison_eligible", "")).lower() in {"true", "1"}
    )


def write_outputs(result_root: Path, rows: Sequence[Dict[str, object]], metadata: Dict[str, object]) -> None:
    write_csv(result_root / "all_results.csv", rows)
    write_text_summary(result_root / "summary.txt", rows, metadata)
    headers: List[str] = []
    seen_headers = set()
    for row in rows:
        for key in row:
            if key not in seen_headers:
                seen_headers.add(key)
                headers.append(key)
    all_values = [[row.get(h, "") for h in headers] for row in rows]
    agg_headers = [
        "sf",
        "category",
        "total",
        "ok",
        "comparison_eligible",
        "schema_only_ok",
        "error",
        "timeout",
        "crashed",
        "avg_elapsed_sec",
    ]
    cause_headers = ["sf", "category", "status", "cause_category", "count", "description"]
    data_headers = ["sf", "data_dir", "resolved_data_dir", "exists", "csv_count", "total_csv_bytes"]
    load_headers = [
        "sf",
        "class_name",
        "status",
        "source_rows",
        "loaded_rows",
        "skipped_rows",
        "placeholder_rows",
        "orphan_edge_mode",
        "loader_mode",
        "source_kind",
        "source_file",
        "source_sha256",
        "source_rows_verified",
        "source_current_match",
        "loader_config_sha256",
        "resume_mode",
        "resume_prefix_rows",
        "resume_prefix_assumption",
        "error",
    ]
    sheets = {
        "per_query": (headers, all_values),
        "by_sf_category": (agg_headers, aggregate_rows(rows)),
        "error_categories": (cause_headers, cause_category_rows(rows)),
        "data_manifests": (data_headers, data_manifest_rows(metadata)),
        "orientdb_load_manifest": (load_headers, orientdb_load_manifest_rows(metadata)),
    }
    write_xlsx(result_root / "summary.xlsx", sheets)


def col_ref(idx: int) -> str:
    letters = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def sheet_xml(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    all_rows = [headers] + list(rows)
    xml_rows = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            ref = f"{col_ref(c_idx)}{r_idx}"
            if value is None or value == "":
                cells.append(f'<c r="{ref}"/>')
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                text = escape(str(value), {'"': "&quot;"})
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )


def write_xlsx(path: Path, sheets: Dict[str, Tuple[Sequence[str], Sequence[Sequence[object]]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_names = []
    for i, name in enumerate(sheets, start=1):
        cleaned = re.sub(r"[\[\]:*?/\\]", "_", name)[:31] or f"Sheet{i}"
        safe_names.append(cleaned)

    workbook_sheets = []
    rels = []
    content_overrides = []
    for i, name in enumerate(safe_names, start=1):
        workbook_sheets.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
        rels.append(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        )
        content_overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
    style_rid = len(safe_names) + 1
    rels.append(
        f'<Relationship Id="rId{style_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            + "".join(content_overrides)
            + "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{"".join(workbook_sheets)}</sheets></workbook>',
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels)
            + "</Relationships>",
        )
        zf.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
            '<borders count="1"><border/></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            "</styleSheet>",
        )
        for i, (headers, rows) in enumerate(sheets.values(), start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(headers, rows))


def write_text_summary(path: Path, rows: Sequence[Dict[str, object]], metadata: Dict[str, object]) -> None:
    by_sf = Counter((r["sf"], r["status"]) for r in rows)
    by_cat = Counter((r["sf"], r["category"], r["status"]) for r in rows)
    cause_categories = Counter(str(r.get("cause_category", "")) for r in rows if r["status"] != "OK")
    cause_by_sf_cat = Counter(
        (str(r["sf"]), str(r["category"]), str(r.get("cause_category", "")))
        for r in rows
        if r["status"] != "OK"
    )
    first_errors = Counter(str(r.get("first_error", "")) for r in rows if r.get("first_error"))
    lines = []
    lines.append("OrientDB GRBench sciscinet query test summary")
    lines.append(f"Generated: {metadata['generated_at']}")
    lines.append(f"OrientDB: {metadata['orientdb_version']}")
    lines.append(f"Query root: {metadata['query_root']}")
    lines.append(f"Load mode: {metadata['load_mode']}")
    if metadata.get("loader_mode"):
        lines.append(f"Loader mode: {metadata['loader_mode']}")
    lines.append("")
    lines.append("Important note:")
    if "data_loaded" in str(metadata.get("load_mode", "")):
        lines.append(
            "This run executes OrientDB-compatible rewrite SQL files against OrientDB databases "
            "with GRBench CSV data imported. OK means execution completed only. A result is eligible "
            "for cross-system comparison only when comparison_eligible=true."
        )
        if metadata.get("loader_mode_note"):
            lines.append(str(metadata["loader_mode_note"]))
    elif str(metadata.get("load_mode", "")).startswith("orientdb_rewritten"):
        lines.append(
            "This run executes generated OrientDB-compatible rewrite SQL files against schema-only "
            "OrientDB databases. Only SQL files present under the query root were executed; the "
            "rewrite manifest records source SQL files that were not safely rewritten. Rows marked "
            "SCHEMA_ONLY_OK parsed/executed only against the empty schema and must not be read as "
            "full data benchmark successes; full CSV import is not performed by this runner."
        )
    else:
        lines.append(
            "This run executes the supplied SQL files as-is against schema-only OrientDB databases. "
            "The SQL/PGQ GRAPH_TABLE and ANSI JOIN workloads fail in OrientDB before data access. "
            "Rows marked SCHEMA_ONLY_OK parsed/executed only against the empty schema and must not be "
            "read as full data benchmark successes; full CSV import is not performed by this runner."
        )
    lines.append("")
    lines.append("Status by scale factor:")
    for sf in SCALE_FACTORS:
        total = sum(v for (s, _), v in by_sf.items() if s == sf)
        parts = [f"{status}={by_sf[(sf, status)]}" for status in sorted({k[1] for k in by_sf if k[0] == sf})]
        lines.append(f"  {sf}: total={total}, " + ", ".join(parts))
    lines.append("")
    lines.append("Status by category:")
    for sf in SCALE_FACTORS:
        lines.append(f"  {sf}:")
        for cat in CATEGORIES:
            total = sum(v for (s, c, _), v in by_cat.items() if s == sf and c == cat)
            parts = [
                f"{status}={by_cat[(sf, cat, status)]}"
                for status in sorted({k[2] for k in by_cat if k[0] == sf and k[1] == cat})
            ]
            lines.append(f"    {cat}: total={total}, " + ", ".join(parts))
    lines.append("")
    lines.append("Cause categories:")
    for cause, count in cause_categories.most_common():
        description = CAUSE_DESCRIPTIONS.get(cause, "No description available.")
        lines.append(f"  [{count}] {cause}: {description}")
    lines.append("")
    lines.append("Cause categories by scale factor and query category:")
    for sf in SCALE_FACTORS:
        if not any(s == sf for s, _, _ in cause_by_sf_cat):
            continue
        lines.append(f"  {sf}:")
        for cat in CATEGORIES:
            parts = [
                f"{cause}={cause_by_sf_cat[(sf, cat, cause)]}"
                for cause in sorted({k[2] for k in cause_by_sf_cat if k[0] == sf and k[1] == cat})
            ]
            if parts:
                lines.append(f"    {cat}: " + ", ".join(parts))
    lines.append("")
    lines.append("Top raw OrientDB error excerpts:")
    for error, count in first_errors.most_common(20):
        lines.append(f"  [{count}] {error[:500]}")
    lines.append("")
    lines.append("Result columns:")
    lines.append(f"  benchmark_contract_version={metadata.get('benchmark_contract_version', '')}.")
    lines.append(
        "  elapsed_sec/time_sec is the benchmark query latency. In warm execution mode it is measured "
        "inside an already-started embedded OrientDB worker from the execution boundary until the "
        "complete result is materialized. Client request/response time is recorded separately; Update "
        "setup, validation, and rollback are outside this window."
    )
    lines.append(
        "  result_sha256 is computed from normalized console result tables. comparison_eligible requires "
        "an exact expected-result hash match; an unverified OK row is not a comparable benchmark result."
    )
    lines.append("  cpu_peak/cpu_avg are aliases of cpu_peak_pct/cpu_avg_pct for cross-system CSV compatibility.")
    lines.append("  mem_peak_mb and mem_avg_mb are resident set size metrics sampled at the configured interval.")
    lines.append(
        "  cause_category is a normalized error bucket; error_cause and first_error retain per-query detail."
    )
    lines.append(
        "  CPU percent is sampled from the OrientDB console process tree and may exceed 100 on multi-core systems."
    )
    path.write_text("\n".join(lines) + "\n")


def aggregate_rows(rows: Sequence[Dict[str, object]]) -> List[List[object]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["sf"]), str(row["category"]))].append(row)
    out: List[List[object]] = []
    for (sf, category), items in sorted(grouped.items(), key=lambda x: (x[0][0], CATEGORIES.index(x[0][1]))):
        statuses = Counter(str(i["status"]) for i in items)
        numeric_elapsed = [float(i["elapsed_sec"]) for i in items if isinstance(i["elapsed_sec"], (int, float))]
        out.append(
            [
                sf,
                category,
                len(items),
                statuses.get("OK", 0),
                sum(str(item.get("comparison_eligible", "")).lower() in {"true", "1"} for item in items),
                statuses.get("SCHEMA_ONLY_OK", 0),
                statuses.get("ERROR", 0),
                statuses.get("TIMEOUT", 0),
                statuses.get("CRASHED", 0),
                round(sum(numeric_elapsed) / len(numeric_elapsed), 6) if numeric_elapsed else "",
            ]
        )
    return out


def cause_category_rows(rows: Sequence[Dict[str, object]]) -> List[List[object]]:
    grouped = Counter(
        (str(r["sf"]), str(r["category"]), str(r.get("status", "")), str(r.get("cause_category", "")))
        for r in rows
        if str(r.get("status", "")) != "OK"
    )
    out: List[List[object]] = []
    for (sf, category, status, cause), count in sorted(
        grouped.items(), key=lambda x: (x[0][0], CATEGORIES.index(x[0][1]), x[0][3])
    ):
        out.append([sf, category, status, cause, count, CAUSE_DESCRIPTIONS.get(cause, "")])
    return out


def data_manifest_rows(metadata: Dict[str, object]) -> List[List[object]]:
    out: List[List[object]] = []
    for manifest in metadata.get("data_manifests", []):
        if not isinstance(manifest, dict):
            continue
        out.append(
            [
                manifest.get("sf", ""),
                manifest.get("data_dir", ""),
                manifest.get("resolved_data_dir", ""),
                manifest.get("exists", ""),
                manifest.get("csv_count", ""),
                manifest.get("total_csv_bytes", ""),
            ]
        )
    return out


def orientdb_load_manifest_rows(metadata: Dict[str, object]) -> List[List[object]]:
    out: List[List[object]] = []
    for row in metadata.get("orientdb_load_manifests", []):
        if not isinstance(row, dict):
            continue
        out.append(
            [
                row.get("sf", ""),
                row.get("class_name", ""),
                row.get("status", ""),
                row.get("source_rows", ""),
                row.get("loaded_rows", ""),
                row.get("skipped_rows", ""),
                row.get("placeholder_rows", ""),
                row.get("orphan_edge_mode", ""),
                row.get("loader_mode", ""),
                row.get("source_kind", ""),
                row.get("source_file", ""),
                row.get("source_sha256", ""),
                row.get("source_rows_verified", ""),
                row.get("source_current_match", ""),
                row.get("loader_config_sha256", ""),
                row.get("resume_mode", ""),
                row.get("resume_prefix_rows", ""),
                row.get("resume_prefix_assumption", ""),
                row.get("error", ""),
            ]
        )
    return out


def run(args: argparse.Namespace) -> int:
    global DATA_ROOT
    DATA_ROOT = Path(args.data_root)
    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.runs % 2 == 0:
        raise SystemExit("--runs must be odd so the median maps to one observed run and its resource metrics")
    if args.resource_sample_interval <= 0:
        raise SystemExit("--resource-sample-interval must be > 0")
    if args.update_setup_timeout <= 0:
        raise SystemExit("--update-setup-timeout must be > 0")
    if args.update_recovery_timeout <= 0:
        raise SystemExit("--update-recovery-timeout must be > 0")
    if args.update_recovery_max_attempts < 1:
        raise SystemExit("--update-recovery-max-attempts must be >= 1")
    if args.update_batch_size < 1:
        raise SystemExit("--update-batch-size must be >= 1")
    if args.warmup_runs < 0:
        raise SystemExit("--warmup-runs must be >= 0")
    if args.worker_max_result_rows < 1:
        raise SystemExit("--worker-max-result-rows must be >= 1")

    orientdb_home = Path(args.orientdb_home)
    java_home = Path(args.java_home)
    if not (orientdb_home / "bin" / "console.sh").exists():
        raise SystemExit(f"OrientDB console not found under {orientdb_home}")
    if not (java_home / "bin" / "java").exists():
        raise SystemExit(f"Java not found under {java_home}")
    if args.execution_mode == "warm":
        compile_benchmark_worker(java_home, orientdb_home)

    result_root = Path(args.results_dir)
    db_root = Path(args.db_dir)
    query_root = Path(args.query_root)
    source_query_root = Path(args.source_query_root)
    queries = discover_queries(query_root)
    if args.category:
        wanted = set(args.category)
        queries = [q for q in queries if q.category in wanted]
    if args.match:
        queries = [q for q in queries if args.match in q.rel_path]
    if args.stop_before_update:
        queries = [q for q in queries if q.category != "update"]
    if args.strict_comparable_only:
        queries = [
            query
            for query in queries
            if not (
                query.category == "update"
                and query.path.name in UPDATE_COMPARABILITY_CLASS
            )
        ]
    selected_sfs = args.sf or SCALE_FACTORS
    if args.limit:
        queries = queries[: args.limit]
    if args.reuse_update_results and args.resume:
        raise SystemExit("--reuse-update-results cannot be combined with --resume")
    reused_update_rows, reused_update_sources = load_reused_update_results(
        args.reuse_update_results,
        selected_sfs,
        queries,
        source_query_root,
        args.runs,
        args.warmup_runs,
        args.resource_sample_interval,
    )
    if any(query.category == "update" for query in queries) and args.execution_mode != "warm":
        raise SystemExit("strict Update execution requires --execution-mode warm")
    expected_results = load_expected_results(args.expected_results)
    expected_results_validation = validate_expected_results(
        expected_results,
        queries,
        source_query_root,
        selected_sfs,
    )
    if (
        "data_loaded" in str(args.load_mode)
        and any(query.category != "update" for query in queries)
        and expected_results_validation["status"] != "PASS"
    ):
        raise SystemExit(
            "data-loaded benchmark requires a valid DuckDB oracle: "
            + "; ".join(str(problem) for problem in expected_results_validation["problems"])
        )

    require_source_provenance = "data_loaded" in str(args.load_mode)
    data_manifests = [
        data_manifest(sf, include_checksums=require_source_provenance)
        for sf in selected_sfs
    ]
    current_loader_config_sha256 = loader_config_sha256()
    accepted_loader_config_sha256s = compatible_loader_config_sha256s()

    load_manifest_rows = [
        row
        for sf in selected_sfs
        for row in query_load_manifest(
            sf,
            db_root,
            orientdb_home,
            java_home,
            args.heap,
            result_root / sf / "manifest_worker.log",
        )
    ]
    source_provenance = validate_source_provenance(
        load_manifest_rows,
        data_manifests,
        current_loader_config_sha256,
        accepted_loader_config_sha256s,
    )
    manifest_rows_by_sf = {
        sf: [row for row in load_manifest_rows if str(row.get("sf", "")) == sf]
        for sf in selected_sfs
    }
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_contract_version": BENCHMARK_CONTRACT_VERSION,
        "orientdb_version": orientdb_version(orientdb_home, java_home),
        "orientdb_home": str(orientdb_home),
        "java_home": str(java_home),
        "query_root": str(query_root),
        "source_query_root": str(source_query_root),
        "query_suite_sha256": query_suite_sha256(queries),
        "source_query_suite_sha256": query_suite_sha256(queries, source_query_root),
        "data_root": str(DATA_ROOT),
        "scale_factors": selected_sfs,
        "query_count_per_sf": len(queries),
        "load_mode": args.load_mode,
        "loader_mode": (
            "workload_projection_native_graph"
            if args.load_mode == "orientdb_manual_data_loaded_native_graph"
            else args.load_mode
        ),
        "loader_mode_note": (
            "OrientDB native graph data-loaded runs import only the workload projection schema, "
            "not every raw CSV file. Missing edge endpoints are represented by typed-external "
            "_MissingEndpoint vertices so source_rows equals loaded_rows without creating false "
            "typed graph matches."
            if args.load_mode == "orientdb_manual_data_loaded_native_graph"
            else ""
        ),
        "timeout_seconds": args.timeout,
        "orientdb_console_heap": args.heap,
        "execution_mode": args.execution_mode,
        "execution_backend": "embedded_worker" if args.execution_mode == "warm" else "cold_console",
        "runs_per_query": args.runs,
        "warmup_runs_per_query": args.warmup_runs,
        "cache_policy": "persistent_session_with_per_query_unmeasured_warmup",
        "time_metric": (
            "worker_pre_execute_to_fully_materialized_result_seconds"
            if args.execution_mode == "warm"
            else "cold_console_end_to_end_seconds"
        ),
        "client_time_metric": "request_write_to_structured_result_received_seconds",
        "update_isolation": UPDATE_ISOLATION_MODE,
        "update_batch_size": args.update_batch_size,
        "update_worker_protocol": UPDATE_WORKER_PROTOCOL,
        "reused_update_results": reused_update_sources,
        "reused_update_result_count": len(reused_update_rows),
        "reused_update_policy": (
            "Rows are validated and included with their original measurements. "
            "Validity is recalculated against this run's required runs and warmups; "
            "a sampling mismatch is never relabeled as comparison eligible."
            if reused_update_rows
            else "not_requested"
        ),
        "update_support_classes": [UPDATE6_AUTHOR_SHADOW, UPDATE_RECOVERY_PROGRESS],
        "update6_vertex_strategy": (
            "move Authors_Gender vertices to an indexed non-subclass shadow while preserving "
            "Authors_Paper edges, then move them back during restore"
        ),
        "update_staging_required_mode": "derived_update_snapshot_v1",
        "update_validation_scope": "exact_affected_class_delta_against_provenance_verified_derived_staging",
        "update_setup_in_timed_window": False,
        "update_setup_timeout_seconds": args.update_setup_timeout,
        "update_recovery_timeout_seconds": args.update_recovery_timeout,
        "update_recovery_max_attempts": args.update_recovery_max_attempts,
        "expected_results_manifest": args.expected_results,
        "expected_results_validation": expected_results_validation,
        "comparison_policy": (
            "comparison_eligible requires execution OK, complete loader manifest for every referenced class, "
            "an exact expected-result hash match, and successful Update compensation verification"
        ),
        "resource_sampling_interval_seconds": args.resource_sample_interval,
        "cpu_time_metric": "worker_process_cpu_time_delta_inside_primary_timing_window",
        "cpu_peak_metric": "sampled_worker_process_tree_cpu_percent",
        "memory_metric": "sampled_worker_process_tree_resident_set_mib",
        "worker_protocol_version": WORKER_PROTOCOL_VERSION,
        "worker_max_result_rows": args.worker_max_result_rows,
        "orientdb_console_max_width": CONSOLE_MAX_WIDTH,
        "resource_note": "CPU percent is sampled from the benchmarked engine process tree and may exceed 100 on multi-core systems; memory MB is resident set size.",
        "data_manifests": data_manifests,
        "orientdb_load_manifests": load_manifest_rows,
        "source_provenance": source_provenance,
        "loader_config_sha256": current_loader_config_sha256,
        "accepted_loader_config_sha256s": accepted_loader_config_sha256s,
        "database_preflights": [],
    }
    result_root.mkdir(parents=True, exist_ok=True)
    (result_root / "metadata.json").write_text(json.dumps(metadata, indent=2))

    rerun_status = set(args.rerun_status or [])
    all_rows: List[Dict[str, object]] = read_csv_rows(result_root / "all_results.csv") if (args.resume or rerun_status) else []
    if args.resume:
        all_rows = [row for row in all_rows if resumable_row(row)]
    if rerun_status:
        all_rows = [r for r in all_rows if str(r.get("status", "")) not in rerun_status]
    done = {(str(r["sf"]), str(r["sql_file"])) for r in all_rows if resumable_row(r)}
    preflight_failed_sfs: List[str] = []
    strict_execution_failures: List[str] = []
    for sf in selected_sfs:
        sf_dir = result_root / sf
        log_dir = sf_dir / "logs"
        db_path = db_root / sf
        create_database(
            db_path=db_path,
            orientdb_home=orientdb_home,
            java_home=java_home,
            log_path=sf_dir / "setup.log",
            rebuild=args.rebuild,
            heap=args.heap,
        )

        rows: List[Dict[str, object]] = read_csv_rows(sf_dir / "per_query.csv") if (args.resume or rerun_status) else []
        if args.resume:
            rows = [row for row in rows if resumable_row(row)]
        if rerun_status:
            rows = [r for r in rows if str(r.get("status", "")) not in rerun_status]
        session: Optional[OrientDBConsoleSession] = None
        try:
            if args.execution_mode == "warm":
                session = OrientDBConsoleSession(
                    db_path=db_path,
                    orientdb_home=orientdb_home,
                    java_home=java_home,
                    heap=args.heap,
                    sample_interval_s=args.resource_sample_interval,
                    session_log_path=sf_dir / "worker_session.log",
                    max_result_rows=args.worker_max_result_rows,
                )
                session.start()
                if "data_loaded" in str(args.load_mode):
                    preflight = database_preflight(
                        session,
                        queries,
                        manifest_rows_by_sf.get(sf, []),
                        args.update_setup_timeout,
                    )
                    preflight["sf"] = sf
                    metadata["database_preflights"].append(preflight)
                    (sf_dir / "database_preflight.json").write_text(
                        json.dumps(preflight, indent=2),
                        encoding="utf-8",
                    )
                    (result_root / "metadata.json").write_text(json.dumps(metadata, indent=2))
                    if preflight["status"] != "PASS":
                        preflight_failed_sfs.append(sf)
                        print(
                            f"[{sf}] ABORT: database preflight failed; see "
                            f"{sf_dir / 'database_preflight.json'}",
                            flush=True,
                        )
                        continue
                    if args.preflight_only:
                        print(f"[{sf}] PASS: strict database preflight", flush=True)
                        continue
            for idx, query in enumerate(queries, start=1):
                if args.resume and (sf, query.rel_path) in done:
                    print(f"[{sf}] {idx}/{len(queries)} SKIP {query.rel_path}", flush=True)
                    continue
                reused_row = reused_update_rows.get((sf, query.rel_path))
                action = "REUSE" if reused_row is not None else "RUN"
                print(
                    f"[{sf}] {idx}/{len(queries)} {action} {query.rel_path}",
                    flush=True,
                )
                success_status = "OK" if "data_loaded" in str(args.load_mode) else "SCHEMA_ONLY_OK"
                if reused_row is not None:
                    row = dict(reused_row)
                elif args.execution_mode == "warm":
                    assert session is not None
                    if query.category == "update":
                        if success_status != "OK":
                            raise SystemExit("Update benchmark requires a data-loaded database")
                        row = run_update_query_file_warm(
                            sf=sf,
                            query=query,
                            session=session,
                            log_dir=log_dir,
                            timeout_s=args.timeout,
                            setup_timeout_s=args.update_setup_timeout,
                            recovery_timeout_s=args.update_recovery_timeout,
                            recovery_max_attempts=args.update_recovery_max_attempts,
                            update_batch_size=args.update_batch_size,
                            success_status=success_status,
                            runs=args.runs,
                            warmup_runs=args.warmup_runs,
                            manifest_rows=manifest_rows_by_sf.get(sf, []),
                            source_query_root=source_query_root,
                        )
                    else:
                        row = run_query_file_warm(
                            sf=sf,
                            query=query,
                            session=session,
                            log_dir=log_dir,
                            timeout_s=args.timeout,
                            success_status=success_status,
                            runs=args.runs,
                            warmup_runs=args.warmup_runs,
                            source_query_root=source_query_root,
                        )
                else:
                    row = run_query_file_cold(
                        sf,
                        query,
                        db_path,
                        orientdb_home,
                        java_home,
                        log_dir,
                        args.timeout,
                        success_status,
                        args.heap,
                        args.resource_sample_interval,
                        source_query_root,
                    )
                row.setdefault("result_origin", "measured_current_run")
                row.setdefault("reused_result", False)
                annotate_result_validity(
                    row,
                    query,
                    manifest_rows_by_sf.get(sf, []),
                    expected_results,
                    args.runs,
                    args.warmup_runs,
                    require_source_provenance=require_source_provenance,
                )
                if require_source_provenance:
                    comparison_eligible = is_true(row.get("comparison_eligible", False))
                    if query.category == "update":
                        comparability_class = str(
                            row.get("update_comparability_class", "CONTRACT_ALIGNED")
                        )
                        if row["status"] != "OK" or (
                            comparability_class == "CONTRACT_ALIGNED" and not comparison_eligible
                        ):
                            strict_execution_failures.append(
                                f"{sf}:{query.rel_path}:{row['status']}"
                            )
                    elif not comparison_eligible:
                        strict_execution_failures.append(
                            f"{sf}:{query.rel_path}:{row['status']}"
                        )
                rows.append(row)
                all_rows.append(row)
                done.add((sf, query.rel_path))
                write_csv(sf_dir / "per_query.csv", rows)
                write_text_summary(sf_dir / "summary.txt", rows, metadata)
                write_outputs(result_root, all_rows, metadata)
                if query.category == "update" and row["status"] in {
                    "BASELINE_CHECK_FAILED",
                    "BASELINE_MISMATCH",
                    "BASELINE_CORRUPTED",
                }:
                    print(
                        f"[{sf}] ABORT remaining queries: strict Update baseline is not trustworthy",
                        flush=True,
                    )
                    break
        finally:
            if session is not None:
                session.close()
        write_csv(sf_dir / "per_query.csv", rows)
        write_text_summary(sf_dir / "summary.txt", rows, metadata)

    if require_source_provenance and not args.preflight_only:
        completed_pairs = {
            (str(row.get("sf", "")), str(row.get("sql_file", "")))
            for row in all_rows
        }
        for sf in selected_sfs:
            for query in queries:
                if (sf, query.rel_path) not in completed_pairs:
                    strict_execution_failures.append(f"{sf}:{query.rel_path}:MISSING")
    metadata["strict_execution_failures"] = sorted(set(strict_execution_failures))
    metadata["strict_execution_status"] = (
        "FAIL" if strict_execution_failures or preflight_failed_sfs else "PASS"
    )
    (result_root / "metadata.json").write_text(json.dumps(metadata, indent=2))
    write_outputs(result_root, all_rows, metadata)
    if preflight_failed_sfs:
        return 2
    return 3 if strict_execution_failures else 0


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf", action="append", choices=SCALE_FACTORS, help="Scale factor to run. Repeatable.")
    parser.add_argument("--category", action="append", choices=CATEGORIES, help="Top-level query category to run. Repeatable.")
    parser.add_argument("--match", default="", help="Only run query files whose relative path contains this substring.")
    parser.add_argument("--limit", type=int, default=0, help="Run only the first N query files per SF.")
    parser.add_argument("--timeout", type=int, default=QUERY_TIMEOUT_S, help="Per SQL file timeout in seconds.")
    parser.add_argument("--rebuild", action="store_true", help="Recreate OrientDB databases under --db-dir.")
    parser.add_argument("--resume", action="store_true", help="Skip queries already present in all_results.csv/per_query.csv.")
    parser.add_argument(
        "--reuse-update-results",
        action="append",
        default=[],
        metavar="RESULT_DIR_OR_CSV",
        help=(
            "Reuse validated Contract-v4 Update rows from an existing result directory or "
            "all_results.csv. The original sampling provenance is preserved and validity is "
            "recalculated against the current --runs/--warmup-runs contract. Repeatable."
        ),
    )
    parser.add_argument(
        "--rerun-status",
        action="append",
        choices=[
            "OK",
            "SCHEMA_ONLY_OK",
            "ERROR",
            "TIMEOUT",
            "CRASHED",
            "DEPENDENCY_FAILED",
            "VALIDATION_FAILED",
            "BASELINE_CHECK_FAILED",
            "BASELINE_MISMATCH",
            "BASELINE_CORRUPTED",
            "UPDATE_INPUT_INVALID",
        ],
        help="Replace existing rows with this status by rerunning those queries.",
    )
    parser.add_argument("--stop-before-update", action="store_true", help="Run only read-only categories and skip the update workload.")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate the complete data, query, and oracle contract without executing benchmark queries.",
    )
    parser.add_argument(
        "--strict-comparable-only",
        action="store_true",
        help="Exclude Update tasks with a declared cross-engine data-model mismatch.",
    )
    parser.add_argument("--orientdb-home", default=str(DEFAULT_ORIENTDB_HOME))
    parser.add_argument("--java-home", default=str(DEFAULT_JAVA_HOME))
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root containing sf10_0, sf10_1, ... CSV directories.",
    )
    parser.add_argument("--query-root", default=str(DEFAULT_QUERY_ROOT), help="Root directory containing GRBench SQL files.")
    parser.add_argument(
        "--source-query-root",
        default=str(DEFAULT_SOURCE_QUERY_ROOT),
        help="Root of the unrewritten source SQL used for provenance and oracle validation.",
    )
    parser.add_argument("--load-mode", default="schema_only", help="Metadata label describing the database/load mode.")
    parser.add_argument("--heap", default=DEFAULT_CONSOLE_HEAP, help="OrientDB console heap for data-loaded benchmark runs.")
    parser.add_argument(
        "--execution-mode",
        choices=["warm", "cold"],
        default="warm",
        help="warm uses the contract timing window; cold preserves the legacy per-query console process timing.",
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of executions per SQL file; elapsed_sec is the median run.")
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=1,
        help="Unmeasured executions per SQL file before measured runs; Update warmups are explicitly compensated.",
    )
    parser.add_argument(
        "--update-setup-timeout",
        type=int,
        default=QUERY_TIMEOUT_S,
        help="Timeout for unmeasured Update setup, compensation, and baseline checks.",
    )
    parser.add_argument(
        "--update-recovery-timeout",
        type=int,
        default=QUERY_TIMEOUT_S,
        help="Per-attempt timeout for resumable Update baseline recovery.",
    )
    parser.add_argument(
        "--update-recovery-max-attempts",
        type=int,
        default=DEFAULT_UPDATE_RECOVERY_MAX_ATTEMPTS,
        help="Maximum restart-and-resume attempts for Update baseline recovery.",
    )
    parser.add_argument(
        "--update-batch-size",
        type=int,
        default=DEFAULT_UPDATE_BATCH_SIZE,
        help="Maximum records committed per native Update batch.",
    )
    parser.add_argument(
        "--expected-results",
        default="",
        help="JSON manifest of canonical result hashes required for comparison_eligible=true.",
    )
    parser.add_argument(
        "--resource-sample-interval",
        type=float,
        default=DEFAULT_RESOURCE_SAMPLE_INTERVAL_S,
        help="CPU/RSS sampling interval in seconds; default 0.01 increases per-query metric resolution.",
    )
    parser.add_argument(
        "--worker-max-result-rows",
        type=int,
        default=DEFAULT_WORKER_MAX_RESULT_ROWS,
        help="Fail instead of silently truncating when a query returns more rows than this limit.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(REPO_ROOT / ".local" / "results" / "orientdb"),
    )
    parser.add_argument(
        "--db-dir",
        default=str(REPO_ROOT / ".local" / "orientdb" / "databases"),
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
