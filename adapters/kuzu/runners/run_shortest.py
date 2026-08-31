"""
Run GRBench sciscinet Shortest_Path_Queries on a Kuzu database.

The source SQL is kept under ``benchmark/queries/canonical`` for provenance.

Kuzu 0.11.3 does not support SQL/PGQ GRAPH_TABLE or ANY SHORTEST directly.
The file-backed Kuzu templates are evaluated at exact path lengths within each
requested range, then reachable endpoints are aggregated. Since the benchmark
queries only return MIN() over endpoint columns, duplicate paths do not change
the result.
"""
import argparse
import csv
import os
import threading
import time
from pathlib import Path

import kuzu
import psutil

from measurement import ensure_csv_schema, run_repeated
from shortest_query_loader import load_shortest_queries

RUNNER_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = RUNNER_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
DEFAULT_DB_DIR = REPO_ROOT / ".local" / "kuzu" / "db"
DEFAULT_RESULTS_DIR = REPO_ROOT / ".local" / "results" / "kuzu"
DEFAULT_SOURCE_DIR = REPO_ROOT / "benchmark" / "queries" / "canonical" / "Shortest_Path_Queries"
DEFAULT_QUERY_ROOT = ADAPTER_DIR / "queries" / "Shortest_Path_Queries"
TIMEOUT_S = 18000
SAMPLE_HZ = 100.0
NCORES = psutil.cpu_count()
TOTAL_MEM = psutil.virtual_memory().total


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset suffix, e.g. sf10_3")
    parser.add_argument("--threads", type=int, default=8, help="Kuzu connection thread count")
    parser.add_argument("--buffer-pool-gib", type=float, default=0.0)
    parser.add_argument("--max-unbounded-depth", type=int, default=8)
    parser.add_argument("--sample-hz", type=float, default=SAMPLE_HZ)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--results", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERY_ROOT)
    parser.add_argument("--source-query-root", type=Path, default=DEFAULT_SOURCE_DIR)
    return parser.parse_args()


ARGS = parse_args()
DATASET = ARGS.dataset
DB_PATH = ARGS.db_dir / f"db_{DATASET}"
SOURCE_DIR = ARGS.source_query_root
QUERY_ROOT = ARGS.query_root
RESULTS = Path(ARGS.results) if ARGS.results else DEFAULT_RESULTS_DIR / f"results_{DATASET}_shortest_sciscinet.csv"
THREADS = ARGS.threads
BUFFER_POOL_BYTES = int(ARGS.buffer_pool_gib * 1024**3)
MAX_UNBOUNDED_DEPTH = ARGS.max_unbounded_depth
SAMPLE_HZ = ARGS.sample_hz


class Sampler(threading.Thread):
    def __init__(self, proc: psutil.Process):
        super().__init__(daemon=True)
        self.proc = proc
        self._stop_evt = threading.Event()
        self._ready_evt = threading.Event()
        self.cpu_samples = []
        self.rss_samples = []
        try:
            self.proc.cpu_percent(interval=None)
            self.cpu_samples.append(self.proc.cpu_percent(interval=None))
            self.rss_samples.append(self.proc.memory_info().rss)
        except psutil.NoSuchProcess:
            pass

    def run(self):
        period = 1.0 / SAMPLE_HZ
        try:
            self.proc.cpu_percent(interval=None)
        except psutil.NoSuchProcess:
            self._ready_evt.set()
            return
        self._ready_evt.set()
        while not self._stop_evt.wait(period):
            try:
                self.cpu_samples.append(self.proc.cpu_percent(interval=None))
                self.rss_samples.append(self.proc.memory_info().rss)
            except psutil.NoSuchProcess:
                break

    def stop(self):
        self._stop_evt.set()

    def start_sampling(self):
        self.start()
        if not self._ready_evt.wait(timeout=1):
            raise TimeoutError("resource sampler did not start")

    def summary(self):
        if not self.cpu_samples:
            try:
                self.cpu_samples = [self.proc.cpu_percent(interval=None)]
                self.rss_samples = [self.proc.memory_info().rss]
            except psutil.NoSuchProcess:
                return 0.0, 0.0, 0.0, 0.0, 0
        cpu_peak_pct = max(self.cpu_samples)
        cpu_avg_pct = sum(self.cpu_samples) / len(self.cpu_samples)
        mem_peak_mb = max(self.rss_samples) / 1024 / 1024
        mem_avg_mb = sum(self.rss_samples) / len(self.rss_samples) / 1024 / 1024
        return cpu_peak_pct, cpu_avg_pct, mem_peak_mb, mem_avg_mb, len(self.rss_samples)


def read_done():
    if not RESULTS.exists():
        return set()
    done = set()
    with RESULTS.open(newline="") as f:
        for row in csv.DictReader(f):
            done.add((row["category"], row["subcategory"], row["sql_file"]))
    return done


def consume(result):
    rows = 0
    first = None
    while result.has_next():
        row = result.get_next()
        rows += 1
        if first is None:
            first = row
    return rows, first


def run_one(db, query):
    out = {
        "status": "OK",
        "rows": 0,
        "elapsed_s": 0.0,
        "cpu_peak_pct": 0.0,
        "cpu_avg_pct": 0.0,
        "mem_peak_mb": 0.0,
        "mem_avg_mb": 0.0,
        "sample_count": 0,
        "result": "",
        "error": "",
    }
    conn = kuzu.Connection(db, num_threads=THREADS)
    proc = psutil.Process(os.getpid())
    sampler = Sampler(proc)
    result_holder = {"rows": 0, "first": None, "exc": None}

    def worker():
        try:
            sampler.start_sampling()
            t0 = time.perf_counter()
            total_rows = 0
            first = None
            matched = False
            values = []
            for depth, sql in enumerate(query["steps"]):
                rows, step_first = consume(conn.execute(sql))
                total_rows += rows
                if step_first is None:
                    continue
                matched_count = step_first[0] or 0
                value = step_first[1] if len(step_first) > 1 else None
                if matched_count > 0:
                    matched = True
                    if value is not None:
                        values.append(value)
            first = [min(values)] if values else ([None] if matched else None)
            result_holder["matched"] = matched
            result_holder["elapsed"] = time.perf_counter() - t0
            result_holder["rows"] = total_rows
            result_holder["first"] = first
        except Exception as exc:
            result_holder["exc"] = exc

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=TIMEOUT_S)
    if th.is_alive():
        out["status"] = "TIMEOUT"
        try:
            conn.interrupt()
        except Exception:
            pass
        th.join(timeout=10)
    sampler.stop()
    sampler.join(timeout=5)

    cpu_peak, cpu_avg, mem_peak, mem_avg, sample_count = sampler.summary()
    out["elapsed_s"] = float(result_holder.get("elapsed", 0.0))
    out["cpu_peak_pct"] = round(cpu_peak, 3)
    out["cpu_avg_pct"] = round(cpu_avg, 3)
    out["mem_peak_mb"] = round(mem_peak, 3)
    out["mem_avg_mb"] = round(mem_avg, 3)
    out["sample_count"] = sample_count

    if result_holder["exc"] is not None and out["status"] == "OK":
        out["status"] = "RUNTIME_ERROR"
        out["error"] = f"{type(result_holder['exc']).__name__}: {result_holder['exc']}"
    elif out["status"] == "OK":
        if query["unbounded"] and not result_holder.get("matched", False):
            out["status"] = "DEPTH_LIMIT_REACHED"
            out["error"] = f"No matching endpoint found up to depth {MAX_UNBOUNDED_DEPTH}"
        out["rows"] = result_holder["rows"]
        if result_holder["first"] is not None:
            out["result"] = repr(result_holder["first"])[:256]
    return out


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Kuzu DB not found: {DB_PATH}")
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Source query directory not found: {SOURCE_DIR}")
    if not QUERY_ROOT.exists():
        raise FileNotFoundError(f"Kuzu query directory not found: {QUERY_ROOT}")
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    if ARGS.overwrite and RESULTS.exists():
        RESULTS.unlink()
    done = read_done()
    db_kwargs = {}
    if BUFFER_POOL_BYTES > 0:
        db_kwargs["buffer_pool_size"] = BUFFER_POOL_BYTES
    db = kuzu.Database(str(DB_PATH), **db_kwargs)
    queries = load_shortest_queries(QUERY_ROOT, MAX_UNBOUNDED_DEPTH)

    print(f"=== Kuzu {DATASET} sciscinet Shortest_Path_Queries benchmark ===")
    print(f"Kuzu={kuzu.__version__}, db={DB_PATH}")
    print(f"Source={SOURCE_DIR}")
    print(f"QueryRoot={QUERY_ROOT}")
    print(f"Queries={len(queries)}, completed={len(done)}, threads={THREADS}, buffer_pool_gib={ARGS.buffer_pool_gib}")
    print(f"Results={RESULTS}")

    columns = [
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
        "result",
        "error",
    ]
    ensure_csv_schema(RESULTS, columns)
    need_header = not RESULTS.exists()
    with RESULTS.open("a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns,
        )
        if need_header:
            writer.writeheader()
        for i, query in enumerate(queries, start=1):
            category = query["category"]
            subcategory = query["subcategory"]
            sql_file = query["sql_file"]
            key = (category, subcategory, sql_file)
            if key in done:
                continue
            out = run_repeated(
                lambda: run_one(db, query),
                warmups=ARGS.warmups,
                repeats=ARGS.repeats,
            )
            row = {
                "category": category,
                "subcategory": subcategory,
                "sql_file": sql_file,
                **out,
            }
            writer.writerow(row)
            f.flush()
            print(
                f"[{i:2d}/{len(queries)}] {subcategory[:36]:36s} {sql_file:7s} "
                f"{out['status']:13s} {out['elapsed_s']:9.4f}s "
                f"cpu={out['cpu_peak_pct']:6.2f}/{out['cpu_avg_pct']:6.2f}% "
                f"mem={out['mem_peak_mb']:9.3f}/{out['mem_avg_mb']:9.3f}MB "
                f"run={out['selected_measured_run']}"
            )
    print("Done.")


if __name__ == "__main__":
    main()
