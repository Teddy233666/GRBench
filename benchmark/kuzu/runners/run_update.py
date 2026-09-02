"""
Run GRBench sciscinet Update tasks on a Kuzu database.

The query IDs and engine-specific templates live under
``benchmark/kuzu/queries/Update``.

The DuckDB workload uses staging tables such as grbench_update1_papers.
This runner loads equivalent staging node/rel tables into the generated Kuzu DB
before timing. Formal repetitions use isolated database copies by default.
"""
import argparse
import csv
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import kuzu
import psutil

from measurement import ensure_csv_schema, run_repeated
from update_query_loader import load_update_tasks

RUNNER_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = RUNNER_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
DEFAULT_DB_DIR = REPO_ROOT / ".local" / "kuzu" / "db"
DEFAULT_RESULTS_DIR = REPO_ROOT / ".local" / "results" / "kuzu"
DEFAULT_UPDATE_SRC = REPO_ROOT / ".local" / "update-staging"
DEFAULT_STAGING_ROOT = REPO_ROOT / ".local" / "kuzu" / "staging"
DEFAULT_UPDATE_STAGING = REPO_ROOT / ".local" / "kuzu" / "update-staging"
DEFAULT_WORK_DB_DIR = REPO_ROOT / ".local" / "kuzu" / "update-work"
DEFAULT_QUERY_ROOT = ADAPTER_DIR / "queries" / "Update"
TIMEOUT_S = 18000
SAMPLE_HZ = 100.0
NCORES = psutil.cpu_count()
TOTAL_MEM = psutil.virtual_memory().total
LINK_KPK_BASE = {
    "link_clinicaltrials": 10_000_000_000,
    "link_newsfeed": 20_000_000_000,
    "link_nih": 40_000_000_000,
    "link_nsf": 50_000_000_000,
}

PAPERS_HEADER = [
    "paperid", "doi", "year", "date", "doctype", "cited_by_count", "is_retracted",
    "reference_count", "citation_count", "C3", "C5", "C10", "disruption",
    "Atyp_Median_Z", "Atyp_10pct_Z", "Atyp_Pairs", "WSB_mu", "WSB_sigma",
    "WSB_Cinf", "SB_B", "SB_T", "team_size", "institution_count", "patent_count",
    "newsfeed_count", "nct_count", "nih_count", "nsf_count",
]
AUTHORS_HEADER = [
    "authorid", "avg_c10", "avg_logc10", "productivity", "h_index", "display_name",
    "inference_sources", "inference_counts", "p_gf",
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset suffix, e.g. sf10_3")
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--buffer-pool-gib", type=float, default=0.0)
    parser.add_argument("--sample-hz", type=float, default=SAMPLE_HZ)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated SQL filenames to run, e.g. 2a.sql,2b.sql.",
    )
    parser.add_argument(
        "--skip",
        default="",
        help="Comma-separated SQL filenames to skip.",
    )
    parser.add_argument(
        "--isolate-copy",
        dest="isolate_copy",
        action="store_true",
        default=True,
        help="Run each task on a reflink/copy of the Kuzu DB instead of using rollback.",
    )
    parser.add_argument(
        "--transaction-rollback",
        dest="isolate_copy",
        action="store_false",
        help="Use transaction rollback instead of a fresh database copy per repetition.",
    )
    parser.add_argument("--results", default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--db-dir", type=Path, default=DEFAULT_DB_DIR)
    parser.add_argument("--update-source", type=Path, default=DEFAULT_UPDATE_SRC)
    parser.add_argument("--staging-root", type=Path, default=DEFAULT_STAGING_ROOT)
    parser.add_argument("--update-staging", type=Path, default=DEFAULT_UPDATE_STAGING)
    parser.add_argument("--work-db-dir", type=Path, default=DEFAULT_WORK_DB_DIR)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERY_ROOT)
    return parser.parse_args()


ARGS = parse_args()
DATASET = ARGS.dataset
DB_PATH = ARGS.db_dir / f"db_{DATASET}"
UPDATE_SRC = ARGS.update_source
STAGING_ROOT = ARGS.staging_root
UPDATE_STAGING = ARGS.update_staging
WORK_DB_DIR = ARGS.work_db_dir
QUERY_ROOT = ARGS.query_root
if ARGS.results:
    RESULTS = Path(ARGS.results)
elif ARGS.isolate_copy:
    RESULTS = DEFAULT_RESULTS_DIR / f"results_{DATASET}_update_sciscinet_isolated.csv"
else:
    RESULTS = DEFAULT_RESULTS_DIR / f"results_{DATASET}_update_sciscinet.csv"
THREADS = ARGS.threads
BUFFER_POOL_BYTES = int(ARGS.buffer_pool_gib * 1024**3)
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


def src(name: str) -> Path:
    path = UPDATE_SRC / name
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def dataset_staging_dir(dataset: str) -> Path:
    if dataset == "sf10_0":
        return STAGING_ROOT / "db_full"
    return STAGING_ROOT / f"staging_{dataset}"


def source_link_twitter_path(dataset: str) -> Path:
    staging_dir = dataset_staging_dir(dataset)
    candidates = [
        staging_dir / "link_twitter.csv",
        staging_dir / "link_twitter_with_rowid.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"link_twitter staging CSV not found for {dataset}: {candidates}")


def prepare_csv(label: str, source: Path, target: Path, header: list[str], row_builder):
    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return target
    t0 = time.time()
    rows = 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("r", newline="", encoding="utf-8") as inf, target.open(
        "w", newline="", encoding="utf-8"
    ) as outf:
        reader = csv.reader(inf)
        writer = csv.writer(outf)
        next(reader)
        writer.writerow(header)
        for idx, row in enumerate(reader, start=1):
            rows += 1
            writer.writerow(row_builder(idx, row))
    print(f"prepare {label:38s} {time.time() - t0:9.2f}s rows={rows}", flush=True)
    return target


def prepare_link_twitter_rel_csv(label: str, source: Path, target: Path) -> Path:
    def row_builder(_idx: int, row: list[str]) -> list[str]:
        if len(row) >= 3:
            return [row[-2], row[-1]]
        return [row[0], row[1]]

    return prepare_csv(label, source, target, ["paperid", "tweet_id"], row_builder)


def prepare_twitter_metadata_csv(dataset: str, source_rel: Path, update_rel: Path) -> Path:
    target = UPDATE_STAGING / f"{dataset}_twitter_metadata_nodes.csv"
    latest_source_mtime = max(source_rel.stat().st_mtime, update_rel.stat().st_mtime)
    if target.exists() and target.stat().st_mtime >= latest_source_mtime:
        return target
    t0 = time.time()
    rows = 0
    seen: set[str] = set()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as outf:
        writer = csv.writer(outf)
        writer.writerow(["tweet_id"])
        for source in (source_rel, update_rel):
            with source.open("r", newline="", encoding="utf-8") as inf:
                reader = csv.reader(inf)
                next(reader)
                for row in reader:
                    tweet_id = row[-1]
                    if tweet_id in seen:
                        continue
                    seen.add(tweet_id)
                    rows += 1
                    writer.writerow([tweet_id])
    print(f"prepare {'twitter_metadata_nodes':38s} {time.time() - t0:9.2f}s rows={rows}", flush=True)
    return target


def prepare_update_csvs(dataset: str):
    UPDATE_STAGING.mkdir(parents=True, exist_ok=True)
    paths = {
        "update1_papers": src("grbench_update1_papers.csv"),
        "update2_edges": src("grbench_update2_edges.csv"),
        "update4_authors": src("grbench_update4_authors_gender.csv"),
    }
    paths["update1_papers_to_authors_rel"] = prepare_csv(
        "update1_papers_to_authors_rel",
        src("grbench_update1_papers_to_authors.csv"),
        UPDATE_STAGING / "grbench_update1_papers_to_authors_rel.csv",
        ["paperid", "authorid", "display_name"],
        lambda _idx, r: [r[0], r[1], ""],
    )
    paths["update3_authors_paper_rel"] = prepare_csv(
        "update3_authors_paper_rel",
        src("grbench_update3_papers_to_authors.csv"),
        UPDATE_STAGING / "grbench_update3_authors_paper_rel.csv",
        ["authorid", "paperid", "display_name"],
        lambda _idx, r: [r[0], r[1], ""],
    )
    paths["update3_paperreferences_rel"] = prepare_csv(
        "update3_paperreferences_rel",
        src("grbench_update3_paperreferences.csv"),
        UPDATE_STAGING / "grbench_update3_paperreferences_rel.csv",
        ["citing_paperid", "cited_paperid", "year", "ref_year", "year_diff"],
        lambda _idx, r: [r[0], r[1], "", "", ""],
    )
    paths["update3_contributed_from_rel"] = prepare_csv(
        "update3_contributed_from_rel",
        src("grbench_update3_contributed_from.csv"),
        UPDATE_STAGING / "grbench_update3_contributed_from_rel.csv",
        ["paperid", "institutionid", "author_position", "authorid", "raw_affiliation_string"],
        lambda _idx, r: [r[0], r[2], "", r[1], ""],
    )
    paths["update3_paperfields_rel"] = prepare_csv(
        "update3_paperfields_rel",
        src("grbench_update3_paperfields.csv"),
        UPDATE_STAGING / "grbench_update3_paperfields_rel.csv",
        ["paperid", "fieldid", "score_openalex"],
        lambda _idx, r: [r[0], r[1], ""],
    )
    paths["update5_papers_to_authors_rel"] = prepare_csv(
        "update5_papers_to_authors_rel",
        src("grbench_update5_papers_to_authors.csv"),
        UPDATE_STAGING / "grbench_update5_papers_to_authors_rel.csv",
        ["paperid", "authorid", "display_name"],
        lambda _idx, r: [r[0], r[1], ""],
    )
    paths["update6_papers_to_authors_rel"] = prepare_csv(
        "update6_papers_to_authors_rel",
        src("grbench_update6_papers_to_authors.csv"),
        UPDATE_STAGING / "grbench_update6_papers_to_authors_rel.csv",
        ["paperid", "authorid", "display_name"],
        lambda _idx, r: [r[0], r[1], ""],
    )
    paths["update6_affiliated_with_rel"] = prepare_csv(
        "update6_affiliated_with_rel",
        src("grbench_update6_affiliated_with.csv"),
        UPDATE_STAGING / "grbench_update6_affiliated_with_rel.csv",
        ["authorid", "institutionid", "author_position"],
        lambda _idx, r: [r[0], r[1], ""],
    )
    link_specs = [
        ("link_clinicaltrials", "grbench_update3_link_clinicaltrials.csv", ["kpk", "paperid", "nct_id"]),
        ("link_newsfeed", "grbench_update3_link_newsfeed.csv", ["kpk", "paperid", "newsfeed_id"]),
        ("link_nih", "grbench_update3_link_nih.csv", ["kpk", "paperid", "award_id"]),
        ("link_nsf", "grbench_update3_link_nsf.csv", ["kpk", "paperid", "award_id"]),
    ]
    for table, filename, header in link_specs:
        paths[f"update3_{table}_node"] = prepare_csv(
            f"update3_{table}_node",
            src(filename),
            UPDATE_STAGING / f"update3_{table}_node.csv",
            header,
            lambda idx, r, base=LINK_KPK_BASE[table]: [base + idx, r[0], r[1]],
        )
    paths["update3_link_twitter_rel"] = prepare_link_twitter_rel_csv(
        "update3_link_twitter_rel",
        src("grbench_update3_link_twitter.csv"),
        UPDATE_STAGING / "grbench_update3_link_twitter_rel.csv",
    )
    return paths


def consume(result):
    rows = 0
    first = None
    while result.has_next():
        row = result.get_next()
        rows += 1
        if first is None:
            first = row
    return rows, first


def exec_stmt(conn, statement: str):
    return consume(conn.execute(statement))


def query_scalar(conn, statement: str):
    result = conn.execute(statement)
    return result.get_next()[0] if result.has_next() else None


def create_tables(conn):
    ddl = [
        """
        CREATE NODE TABLE Update1_Papers(
            paperid STRING PRIMARY KEY, doi STRING, year INT64, date STRING,
            doctype STRING, cited_by_count INT64, is_retracted STRING,
            reference_count INT64, citation_count INT64,
            C3 INT64, C5 INT64, C10 INT64,
            disruption STRING, Atyp_Median_Z STRING, Atyp_10pct_Z STRING, Atyp_Pairs STRING,
            WSB_mu STRING, WSB_sigma STRING, WSB_Cinf STRING, SB_B STRING, SB_T STRING,
            team_size INT64, institution_count INT64, patent_count INT64,
            newsfeed_count INT64, nct_count INT64, nih_count INT64, nsf_count INT64
        );
        """,
        """
        CREATE NODE TABLE Update4_Authors_Gender(
            authorid STRING PRIMARY KEY, avg_c10 STRING, avg_logc10 STRING,
            productivity INT64, h_index INT64, display_name STRING,
            inference_sources INT64, inference_counts INT64, p_gf STRING
        );
        """,
        "CREATE REL TABLE Update2_Edges(FROM Papers TO Papers, year INT64, ref_year INT64, year_diff INT64);",
        "CREATE REL TABLE Update5_Papers_to_Authors(FROM Papers TO Authors_Gender, display_name STRING);",
    ]
    for statement in ddl:
        try:
            exec_stmt(conn, statement)
        except Exception as exc:
            if "already exists" not in str(exc):
                raise


def copy_table(conn, table: str, path: Path, rel: bool = False):
    exec_stmt(conn, f"COPY {table} FROM '{path}' (HEADER=true, IGNORE_ERRORS=true);")
    if rel:
        return query_scalar(conn, f"MATCH ()-[r:{table}]->() RETURN count(*);")
    return query_scalar(conn, f"MATCH (n:{table}) RETURN count(*);")


def ensure_staging_loaded(conn, paths):
    create_tables(conn)
    loads = [
        ("Update1_Papers", paths["update1_papers"], False),
        ("Update4_Authors_Gender", paths["update4_authors"], False),
        ("Update2_Edges", paths["update2_edges"], True),
        ("Update5_Papers_to_Authors", paths["update5_papers_to_authors_rel"], True),
    ]
    for table, path, rel in loads:
        existing = query_scalar(
            conn,
            f"MATCH ()-[r:{table}]->() RETURN count(*);" if rel else f"MATCH (n:{table}) RETURN count(*);",
        )
        if existing:
            print(f"stage {table:28s} already loaded count={existing}", flush=True)
            continue
        t0 = time.time()
        count = copy_table(conn, table, path, rel=rel)
        print(f"stage {table:28s} {time.time() - t0:9.2f}s count={count}", flush=True)


def read_done():
    if not RESULTS.exists():
        return set()
    done = set()
    with RESULTS.open(newline="") as f:
        for row in csv.DictReader(f):
            done.add((row["category"], row["description"], row["sql_file"]))
    return done


def run_statements(conn, statements):
    rows = 0
    first = None
    for statement in statements:
        got_rows, got_first = exec_stmt(conn, statement)
        rows += got_rows
        if first is None:
            first = got_first
    return rows, first


def run_one(db, task):
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
    sampler_started = False
    result_holder = {"rows": 0, "first": None, "exc": None}
    measured_started = threading.Event()

    def worker():
        try:
            nonlocal sampler_started
            conn.execute("BEGIN TRANSACTION;")
            try:
                run_statements(conn, task["setup"])
                sampler.start_sampling()
                sampler_started = True
                measured_started.set()
                t0 = time.perf_counter()
                rows, first = run_statements(conn, task["statements"])
                result_holder["elapsed"] = time.perf_counter() - t0
                result_holder["rows"] = rows
                result_holder["first"] = first
            finally:
                if sampler_started:
                    sampler.stop()
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
        except Exception as exc:
            result_holder["exc"] = exc
            measured_started.set()

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    measured_started.wait(timeout=TIMEOUT_S)
    th.join(timeout=TIMEOUT_S)
    if th.is_alive():
        out["status"] = "TIMEOUT"
        result_holder["elapsed"] = TIMEOUT_S
        try:
            conn.interrupt()
        except Exception:
            pass
        th.join(timeout=10)
    sampler.stop()
    if sampler_started:
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
        out["rows"] = result_holder["rows"]
        if result_holder["first"] is not None:
            out["result"] = repr(result_holder["first"])[:256]
    return out


def remove_db_copy(path: Path):
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for sidecar in path.parent.glob(path.name + ".*"):
        if sidecar.is_dir():
            shutil.rmtree(sidecar)
        else:
            sidecar.unlink()


def copy_database(src_path: Path, dst_path: Path):
    remove_db_copy(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if src_path.is_dir():
        shutil.copytree(src_path, dst_path, copy_function=shutil.copy2)
        return
    subprocess.run(["cp", "--reflink=auto", str(src_path), str(dst_path)], check=True)
    for sidecar in src_path.parent.glob(src_path.name + ".*"):
        target = dst_path.parent / sidecar.name.replace(src_path.name, dst_path.name, 1)
        if sidecar.is_dir():
            shutil.copytree(sidecar, target, copy_function=shutil.copy2)
        else:
            subprocess.run(["cp", "--reflink=auto", str(sidecar), str(target)], check=True)


def run_one_isolated(task, paths, source_db_path: Path):
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
    work_db_path = WORK_DB_DIR / f"db_{DATASET}_{task['sql_file'].replace('.', '_')}_{os.getpid()}"
    copy_database(source_db_path, work_db_path)
    db_kwargs = {}
    if BUFFER_POOL_BYTES > 0:
        db_kwargs["buffer_pool_size"] = BUFFER_POOL_BYTES
    db = kuzu.Database(str(work_db_path), **db_kwargs)
    conn = kuzu.Connection(db, num_threads=THREADS)
    ensure_staging_loaded(conn, paths)
    proc = psutil.Process(os.getpid())
    sampler = Sampler(proc)
    sampler_started = False
    result_holder = {"rows": 0, "first": None, "exc": None}
    measured_started = threading.Event()

    def worker():
        try:
            nonlocal sampler_started
            run_statements(conn, task["setup"])
            sampler.start_sampling()
            sampler_started = True
            measured_started.set()
            t0 = time.perf_counter()
            rows, first = run_statements(conn, task["statements"])
            result_holder["elapsed"] = time.perf_counter() - t0
            result_holder["rows"] = rows
            result_holder["first"] = first
            sampler.stop()
        except Exception as exc:
            result_holder["exc"] = exc
            measured_started.set()

    try:
        th = threading.Thread(target=worker, daemon=True)
        th.start()
        measured_started.wait(timeout=TIMEOUT_S)
        th.join(timeout=TIMEOUT_S)
        if th.is_alive():
            out["status"] = "TIMEOUT"
            result_holder["elapsed"] = TIMEOUT_S
            try:
                conn.interrupt()
            except Exception:
                pass
            th.join(timeout=10)
        sampler.stop()
        if sampler_started:
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
            out["rows"] = result_holder["rows"]
            if result_holder["first"] is not None:
                out["result"] = repr(result_holder["first"])[:256]
    finally:
        try:
            del conn
            del db
        except Exception:
            pass
        remove_db_copy(work_db_path)
    return out


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Kuzu DB not found: {DB_PATH}")
    if not UPDATE_SRC.exists():
        raise FileNotFoundError(f"Update source directory not found: {UPDATE_SRC}")
    if not QUERY_ROOT.exists():
        raise FileNotFoundError(f"Kuzu Update query directory not found: {QUERY_ROOT}")

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    if ARGS.overwrite and RESULTS.exists():
        RESULTS.unlink()
    paths = prepare_update_csvs(DATASET)
    db_kwargs = {}
    if BUFFER_POOL_BYTES > 0:
        db_kwargs["buffer_pool_size"] = BUFFER_POOL_BYTES
    db = None
    conn = None

    print(f"=== Kuzu {DATASET} sciscinet Update benchmark ===")
    print(f"Kuzu={kuzu.__version__}, db={DB_PATH}")
    print(f"Update source={UPDATE_SRC}")
    print(f"Query root={QUERY_ROOT}")
    print(f"threads={THREADS}, buffer_pool_gib={ARGS.buffer_pool_gib}, isolate_copy={ARGS.isolate_copy}")
    session_db_path = WORK_DB_DIR / f"db_{DATASET}_session_{os.getpid()}"
    print(f"copy db: {DB_PATH} -> {session_db_path}")
    copy_database(DB_PATH, session_db_path)
    db = kuzu.Database(str(session_db_path), **db_kwargs)
    conn = kuzu.Connection(db, num_threads=THREADS)
    ensure_staging_loaded(conn, paths)

    tasks = load_update_tasks(QUERY_ROOT, paths)
    only = {item.strip() for item in ARGS.only.split(",") if item.strip()}
    skip = {item.strip() for item in ARGS.skip.split(",") if item.strip()}
    if only:
        tasks = [task for task in tasks if task["sql_file"] in only]
    if skip:
        tasks = [task for task in tasks if task["sql_file"] not in skip]
    done = read_done()
    print(f"Queries={len(tasks)}, completed={len(done)}")
    print(f"Results={RESULTS}")

    columns = [
        "category",
        "description",
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
        "isolation_mode",
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
        for i, task in enumerate(tasks, start=1):
            key = ("Update", task["description"], task["sql_file"])
            if key in done:
                continue
            if ARGS.isolate_copy:
                run_once = lambda: run_one_isolated(task, paths, session_db_path)
            else:
                run_once = lambda: run_one(db, task)
            out = run_repeated(
                run_once,
                warmups=ARGS.warmups,
                repeats=ARGS.repeats,
            )
            row = {
                "category": "Update",
                "description": task["description"],
                "sql_file": task["sql_file"],
                "isolation_mode": "database_copy" if ARGS.isolate_copy else "transaction_rollback",
                **out,
            }
            writer.writerow(row)
            f.flush()
            print(
                f"[{i:2d}/{len(tasks)}] {task['sql_file']:7s} {out['status']:13s} "
                f"{out['elapsed_s']:9.4f}s cpu={out['cpu_peak_pct']:6.2f}/{out['cpu_avg_pct']:6.2f}% "
                f"mem={out['mem_peak_mb']:9.3f}/{out['mem_avg_mb']:9.3f}MB "
                f"run={out['selected_measured_run']}"
            )
    try:
        del conn
        del db
    except Exception:
        pass
    remove_db_copy(session_db_path)
    print("Done.")


if __name__ == "__main__":
    main()
