#!/usr/bin/env python3
"""Run Kuzu Cypher queries in one warm session and measure child-process RSS."""
from __future__ import annotations

import argparse
import csv
import hashlib
import multiprocessing as mp
import os
import queue
import time
from pathlib import Path
from typing import Any

import kuzu
import psutil

from measurement import ensure_csv_schema, run_repeated


RUNNER_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = RUNNER_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
DEFAULT_DB_DIR = REPO_ROOT / ".local" / "kuzu" / "db"
DEFAULT_QUERIES_DIR = ADAPTER_DIR / "queries"
SAMPLE_HZ = 100.0
TIMEOUT_S = 18_000
READY_TIMEOUT_S = 600
NCORES = psutil.cpu_count() or 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERIES_DIR)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--buffer-pool-gib", type=float, default=0.0)
    parser.add_argument("--timeout-s", type=float, default=TIMEOUT_S)
    parser.add_argument("--ready-timeout-s", type=float, default=READY_TIMEOUT_S)
    parser.add_argument("--sample-hz", type=float, default=SAMPLE_HZ)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--sql-files", default="")
    parser.add_argument("--category", default="")
    parser.add_argument(
        "--skip-relational-equivalents",
        "--skip-pure-join",
        action="store_true",
        default=True,
        dest="skip_relational_equivalents",
    )
    parser.add_argument(
        "--include-relational-equivalents",
        "--include-pure-join",
        action="store_false",
        dest="skip_relational_equivalents",
    )
    parser.add_argument("--dedupe-content", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def dataset_db_path(dataset: str, db_dir: Path) -> Path:
    path = db_dir / f"db_{dataset}"
    if path.exists():
        return path
    if dataset == "sf10_0":
        fallback = db_dir / "db_full"
        if fallback.exists():
            return fallback
    return path


def sql_sort_key(name: str) -> tuple[int, str]:
    stem = Path(name).stem
    digits = ""
    suffix = ""
    for char in stem:
        if char.isdigit() and suffix == "":
            digits += char
        else:
            suffix += char
    return int(digits or 10**9), suffix


def query_key(path: Path, query_root: Path) -> tuple[str, str, str]:
    rel = path.relative_to(query_root)
    category = rel.parts[0]
    if category == "Relational_Equivalent_Queries":
        subcategory = Path(*rel.parts[1:-1]).as_posix() if len(rel.parts) > 2 else "."
    else:
        parent = path.parent.relative_to(query_root / category)
        subcategory = parent.as_posix() if str(parent) != "." else "."
    return category, subcategory, path.with_suffix(".sql").name


def find_queries(args: argparse.Namespace) -> list[tuple[str, str, str, Path]]:
    requested = {item.strip() for item in args.sql_files.split(",") if item.strip()}
    requested |= {Path(item).with_suffix(".sql").name for item in list(requested)}
    queries = []
    seen_hashes = set()
    for path in args.query_root.rglob("*.cypher"):
        category, subcategory, sql_file = query_key(path, args.query_root)
        if category == "Shortest_Path_Queries":
            continue
        if args.skip_relational_equivalents and category == "Relational_Equivalent_Queries":
            continue
        if args.category and category != args.category:
            continue
        if requested and sql_file not in requested and path.name not in requested:
            continue
        if args.dedupe_content:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
        queries.append((category, subcategory, sql_file, path))
    return sorted(queries, key=lambda item: (item[0], item[1], sql_sort_key(item[2])))


def read_done(path: Path, dataset: str) -> set[tuple[str, str, str, str]]:
    if not path.exists():
        return set()
    with path.open(newline="") as f:
        return {
            (row.get("dataset", ""), row["category"], row["subcategory"], row["sql_file"])
            for row in csv.DictReader(f)
            if row.get("dataset", "") == dataset
        }


def mb(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return round(float(value) / 1024 / 1024, 3)


def worker_loop(
    db_path: str,
    threads: int,
    buffer_pool_bytes: int,
    request_queue: mp.Queue,
    response_queue: mp.Queue,
) -> None:
    try:
        kwargs: dict[str, Any] = {}
        if buffer_pool_bytes > 0:
            kwargs["buffer_pool_size"] = buffer_pool_bytes
        db = kuzu.Database(db_path, **kwargs)
        conn = kuzu.Connection(db, num_threads=threads)
        proc = psutil.Process(os.getpid())
        response_queue.put(
            {
                "event": "ready",
                "pid": os.getpid(),
                "kuzu_version": kuzu.__version__,
                "warm_rss_mb": mb(proc.memory_info().rss),
            }
        )
        while True:
            request = request_queue.get()
            if request is None:
                break
            query_id = request["query_id"]
            cypher = request["cypher"]
            try:
                start = time.perf_counter()
                result = conn.execute(cypher)
                rows = 0
                first = None
                while result.has_next():
                    row = result.get_next()
                    if first is None:
                        first = row
                    rows += 1
                elapsed = time.perf_counter() - start
                response_queue.put(
                    {
                        "event": "done",
                        "query_id": query_id,
                        "status": "OK",
                        "rows": rows,
                        "elapsed_s": elapsed,
                        "result": repr(first)[:256] if first is not None else "",
                        "error": "",
                        "final_rss_mb": mb(proc.memory_info().rss),
                    }
                )
            except Exception as exc:
                response_queue.put(
                    {
                        "event": "done",
                        "query_id": query_id,
                        "status": "RUNTIME_ERROR",
                        "rows": 0,
                        "elapsed_s": 0.0,
                        "result": "",
                        "error": f"{type(exc).__name__}: {exc}",
                        "final_rss_mb": mb(proc.memory_info().rss),
                    }
                )
    except Exception as exc:
        response_queue.put({"event": "fatal", "error": f"{type(exc).__name__}: {exc}"})


def wait_for_ready(response_queue: mp.Queue, timeout_s: float) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            message = response_queue.get(timeout=min(0.25, max(0.0, deadline - time.time())))
        except queue.Empty:
            continue
        if message.get("event") == "ready":
            return message
        if message.get("event") == "fatal":
            raise RuntimeError(message.get("error", "Kuzu worker failed before ready"))
    raise TimeoutError(f"Kuzu worker was not ready within {timeout_s}s")


def run_query_warm(
    child: psutil.Process,
    request_queue: mp.Queue,
    response_queue: mp.Queue,
    query_id: int,
    cypher: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    request_queue.put({"query_id": query_id, "cypher": cypher})
    child.cpu_percent(interval=None)
    period = 1.0 / args.sample_hz
    deadline = time.time() + args.timeout_s
    rss_samples = []
    cpu_samples = []
    done = None
    while time.time() < deadline:
        try:
            message = response_queue.get(timeout=period)
            if message.get("event") == "done" and message.get("query_id") == query_id:
                done = message
                break
            if message.get("event") == "fatal":
                done = {
                    "status": "RUNTIME_ERROR",
                    "rows": 0,
                    "elapsed_s": 0.0,
                    "result": "",
                    "error": message.get("error", "Kuzu worker fatal error"),
                    "final_rss_mb": 0.0,
                }
                break
        except queue.Empty:
            pass
        try:
            rss_samples.append(child.memory_info().rss)
            cpu_samples.append(child.cpu_percent(interval=None))
        except psutil.NoSuchProcess:
            done = {
                "status": "PROCESS_EXITED",
                "rows": 0,
                "elapsed_s": 0.0,
                "result": "",
                "error": "Kuzu worker process exited during query",
                "final_rss_mb": 0.0,
            }
            break
    if done is None:
        done = {
            "status": "TIMEOUT",
            "rows": 0,
            "elapsed_s": args.timeout_s,
            "result": "",
            "error": f"Query did not finish within {args.timeout_s}s",
            "final_rss_mb": mb(rss_samples[-1]) if rss_samples else 0.0,
        }
    final_rss_bytes = int(float(done.get("final_rss_mb") or 0.0) * 1024 * 1024)
    if final_rss_bytes > 0:
        rss_samples.append(final_rss_bytes)
    mem_peak = mb(max(rss_samples)) if rss_samples else float(done.get("final_rss_mb") or 0.0)
    mem_avg = mb(sum(rss_samples) / len(rss_samples)) if rss_samples else float(done.get("final_rss_mb") or 0.0)
    return {
        "status": done.get("status", "RUNTIME_ERROR"),
        "rows": done.get("rows", 0),
        "elapsed_s": float(done.get("elapsed_s", 0.0)),
        "cpu_peak_pct": round(max(cpu_samples) if cpu_samples else 0.0, 3),
        "cpu_avg_pct": round(sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0, 3),
        "mem_peak_mb": round(float(mem_peak), 3),
        "mem_avg_mb": round(float(mem_avg), 3),
        "sample_count": len(rss_samples),
        "result": done.get("result", ""),
        "error": done.get("error", ""),
        "worker_final_rss_mb": done.get("final_rss_mb", ""),
    }


def main() -> None:
    args = parse_args()
    db_path = dataset_db_path(args.dataset, args.db_dir)
    if not db_path.exists():
        raise FileNotFoundError(f"Kuzu DB not found: {db_path}")
    queries = find_queries(args)
    if not queries:
        raise SystemExit("No matching queries found.")
    args.results.parent.mkdir(parents=True, exist_ok=True)
    if args.overwrite and args.results.exists():
        args.results.unlink()

    cols = [
        "dataset",
        "suite",
        "measurement_mode",
        "db_path",
        "worker_pid",
        "worker_warm_rss_mb",
        "category",
        "subcategory",
        "sql_file",
        "status",
        "rows",
        "elapsed_s",
        "cpu_peak_pct",
        "cpu_avg_pct",
        "mem_peak_mb",
        "mem_avg_mb",
        "sample_count",
        "warmup_runs",
        "warmup_runs_completed",
        "measured_runs",
        "measured_runs_completed",
        "selected_measured_run",
        "measured_elapsed_s",
        "measured_statuses",
        "repeat_consistent",
        "threads",
        "buffer_pool_gib",
        "kuzu_version",
        "query_path",
        "worker_final_rss_mb",
        "result",
        "error",
    ]
    ensure_csv_schema(args.results, cols)

    ctx = mp.get_context("spawn")
    request_queue = ctx.Queue()
    response_queue = ctx.Queue()
    buffer_pool_bytes = int(args.buffer_pool_gib * 1024**3)
    proc = ctx.Process(
        target=worker_loop,
        args=(str(db_path), args.threads, buffer_pool_bytes, request_queue, response_queue),
    )
    proc.start()
    ready = wait_for_ready(response_queue, args.ready_timeout_s)
    child = psutil.Process(proc.pid)
    done_keys = read_done(args.results, args.dataset)

    need_header = not args.results.exists()
    print(f"=== Kuzu warm-session RSS benchmark: {args.dataset} ===")
    print(f"db={db_path}, worker_pid={proc.pid}, warm_rss={ready['warm_rss_mb']}MB")
    print(f"queries={len(queries)}, results={args.results}")
    try:
        with args.results.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cols)
            if need_header:
                writer.writeheader()
            for index, (category, subcategory, sql_file, path) in enumerate(queries, start=1):
                key = (args.dataset, category, subcategory, sql_file)
                if key in done_keys:
                    continue
                invocation = 0

                def run_once() -> dict[str, Any]:
                    nonlocal invocation
                    invocation += 1
                    query_id = index * 100 + invocation
                    return run_query_warm(
                        child,
                        request_queue,
                        response_queue,
                        query_id,
                        path.read_text(),
                        args,
                    )

                out = run_repeated(
                    run_once,
                    warmups=args.warmups,
                    repeats=args.repeats,
                )
                row = {
                    "dataset": args.dataset,
                    "suite": "main_queries",
                    "measurement_mode": "warm_session_child_process_rss",
                    "db_path": str(db_path),
                    "worker_pid": proc.pid,
                    "worker_warm_rss_mb": ready["warm_rss_mb"],
                    "category": category,
                    "subcategory": subcategory,
                    "sql_file": sql_file,
                    "threads": args.threads,
                    "buffer_pool_gib": args.buffer_pool_gib,
                    "kuzu_version": ready.get("kuzu_version", ""),
                    "query_path": str(path),
                    **out,
                }
                writer.writerow(row)
                f.flush()
                print(
                    f"[{index:3d}/{len(queries)}] {sql_file:8s} {out['status']:13s} "
                    f"{out['elapsed_s']:9.4f}s mem={out['mem_peak_mb']:10.3f}/"
                    f"{out['mem_avg_mb']:10.3f}MB samples={out['sample_count']}",
                    flush=True,
                )
                if out["status"] in {"TIMEOUT", "PROCESS_EXITED"}:
                    break
    finally:
        try:
            request_queue.put(None)
        except Exception:
            pass
        proc.join(timeout=20)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=10)


if __name__ == "__main__":
    main()
