"""
Build a Kuzu database for a GRBench dataset using the schema expected by
queries_cypher/.

The default paths are repository-relative and can be overridden with CLI
arguments or ``GRBENCH_DATA_ROOT``.
"""
import argparse
import csv
import os
import re
import shutil
import time
from pathlib import Path

import kuzu

ADAPTER_DIR = Path(__file__).resolve().parent
REPO_ROOT = ADAPTER_DIR.parents[1]
DB_DIR = REPO_ROOT / ".local" / "kuzu" / "db"
STAGING_ROOT = REPO_ROOT / ".local" / "kuzu" / "staging"
GRBENCH_DIR = Path(os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / ".local" / "data"))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="sf10_1", help="GRBench dataset directory name, e.g. sf10_2")
    parser.add_argument(
        "--csv-dir",
        default=None,
        help="Override CSV directory. Defaults to grbench/<dataset>, then grbench/<dataset>_postgresql.",
    )
    parser.add_argument(
        "--db-dir",
        default=str(DB_DIR),
        help="Directory for Kuzu databases.",
    )
    parser.add_argument(
        "--staging-root",
        default=str(STAGING_ROOT),
        help="Directory for rewritten staging CSVs.",
    )
    parser.add_argument("--threads", type=int, default=8, help="Kuzu connection thread count")
    parser.add_argument(
        "--buffer-pool-gib",
        type=float,
        default=0.0,
        help="Kuzu buffer pool size in GiB; 0 uses Kuzu default",
    )
    parser.add_argument(
        "--reuse-staging",
        action="store_true",
        help="Reuse existing rewritten staging CSVs instead of deleting and regenerating them.",
    )
    parser.add_argument(
        "--skip-counts",
        action="store_true",
        help="Skip post-COPY MATCH count probes, useful for very large imports.",
    )
    parser.add_argument(
        "--resume-rels",
        action="store_true",
        help="Open an existing database and load only relationship tables.",
    )
    parser.add_argument(
        "--reset-rels",
        action="store_true",
        help="With --resume-rels, drop and recreate relationship tables before loading them.",
    )
    parser.add_argument(
        "--strict-rel-copy",
        action="store_true",
        help="Do not use IGNORE_ERRORS=true when copying relationship tables.",
    )
    parser.add_argument(
        "--only-rels",
        default="",
        help="Comma-separated relationship tables to load; empty loads all.",
    )
    parser.add_argument(
        "--skip-rels",
        default="",
        help="Comma-separated relationship tables to skip while loading.",
    )
    return parser.parse_args()


ARGS = parse_args()
DATASET = ARGS.dataset
DB_DIR = Path(ARGS.db_dir)
STAGING_ROOT = Path(ARGS.staging_root)


def resolve_csv_dir() -> Path:
    if ARGS.csv_dir:
        return Path(ARGS.csv_dir)
    direct = GRBENCH_DIR / DATASET
    postgres = GRBENCH_DIR / f"{DATASET}_postgresql"
    if direct.is_dir():
        return direct
    if postgres.is_dir():
        return postgres
    return direct


CSV_DIR = resolve_csv_dir()
DB_PATH = DB_DIR / f"db_{DATASET}"
STAGING = STAGING_ROOT / f"staging_{DATASET}"
THREADS = ARGS.threads
BUFFER_POOL_BYTES = int(ARGS.buffer_pool_gib * 1024**3)
REUSE_STAGING = ARGS.reuse_staging
SKIP_COUNTS = ARGS.skip_counts
RESUME_RELS = ARGS.resume_rels
RESET_RELS = ARGS.reset_rels
STRICT_REL_COPY = ARGS.strict_rel_copy


def parse_name_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


ONLY_RELS = parse_name_set(ARGS.only_rels)
SKIP_RELS = parse_name_set(ARGS.skip_rels)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def clean_database() -> None:
    if RESUME_RELS:
        return
    remove_path(DB_PATH)
    for sidecar in DB_PATH.parent.glob(DB_PATH.name + ".*"):
        remove_path(sidecar)
    if not REUSE_STAGING:
        remove_path(STAGING)


def timed(label, fn):
    t0 = time.time()
    result = fn()
    elapsed = time.time() - t0
    print(f"{label:48s} {elapsed:9.2f}s  {result or ''}", flush=True)
    return result


def read_header(path: Path) -> list[str]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def rewrite_csv(src: Path, dst: Path, header, row_builder) -> Path:
    with src.open("r", newline="", encoding="utf-8") as inf, dst.open(
        "w", newline="", encoding="utf-8"
    ) as outf:
        reader = csv.reader(inf)
        writer = csv.writer(outf)
        next(reader)
        writer.writerow(header)
        for idx, row in enumerate(reader, start=1):
            writer.writerow(row_builder(idx, row))
    return dst


def numbered_sources(prefix: str) -> list[Path]:
    pattern = re.compile(rf"^{re.escape(prefix)}_?(\d+)\.csv$")
    found = []
    for path in CSV_DIR.glob(f"{prefix}*.csv"):
        match = pattern.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    return [path for _idx, path in sorted(found)]


def source_files(name: str, *, prefix: str | None = None, alternatives=()) -> list[Path]:
    if prefix:
        shards = numbered_sources(prefix)
        base = CSV_DIR / name
        if base.exists() and shards:
            return [base, *shards]
        if shards:
            return shards
    for candidate in (name, *alternatives):
        path = CSV_DIR / candidate
        if path.exists():
            return [path]
    return []


def project_csvs(label: str, srcs: list[Path], header: list[str], row_builder) -> list[Path]:
    outputs = []
    row_seq = 0
    multi = len(srcs) > 1
    reused_any = False
    for src_idx, src in enumerate(srcs, start=1):
        suffix = f"_{src_idx}" if multi else ""
        dst = STAGING / f"{label}{suffix}.csv"
        if REUSE_STAGING and dst.exists():
            timed(f"reuse {label}{suffix}", lambda d=dst: f"size={d.stat().st_size}")
            outputs.append(dst)
            reused_any = True
            continue
        if REUSE_STAGING and reused_any:
            raise RuntimeError(
                f"Partial staging reuse for {label}: {dst} is missing after earlier shard was reused"
            )

        def write_one(s=src, d=dst):
            nonlocal row_seq
            rows = 0
            with s.open("r", newline="", encoding="utf-8") as inf, d.open(
                "w", newline="", encoding="utf-8"
            ) as outf:
                reader = csv.reader(inf)
                writer = csv.writer(outf)
                next(reader)
                writer.writerow(header)
                for row in reader:
                    row_seq += 1
                    rows += 1
                    writer.writerow(row_builder(row_seq, row))
            return f"rows={rows}"

        timed(f"prepare {label}{suffix}", write_one)
        outputs.append(dst)
    return outputs


def prepare_direct_or_project(
    label: str,
    srcs: list[Path],
    header: list[str],
    row_builder=None,
) -> list[Path]:
    if not srcs:
        print(f"{'prepare ' + label:48s} {'0.00s':>9s}  missing; leave empty", flush=True)
        return []
    if len(srcs) == 1 and row_builder is None and len(read_header(srcs[0])) == len(header):
        return srcs
    if row_builder is None:
        row_builder = lambda _idx, row: row
    return project_csvs(label, srcs, header, row_builder)


def prepend_rowid_paths(label: str, srcs: list[Path], header: list[str]) -> list[Path]:
    if not srcs:
        print(f"{'prepare ' + label:48s} {'0.00s':>9s}  missing; leave empty", flush=True)
        return []
    if len(srcs) == 1 and len(read_header(srcs[0])) == len(header):
        return srcs
    return project_csvs(label, srcs, header, lambda idx, row: [idx, *row])


def query_one(conn, cypher: str):
    result = conn.execute(cypher)
    return result.get_next() if result.has_next() else None


def copy_table(conn, table: str, paths, rel: bool = False) -> str:
    if isinstance(paths, Path):
        paths = [paths]
    options = "HEADER=true"
    if not (rel and STRICT_REL_COPY):
        options += ", IGNORE_ERRORS=true"
    for path in paths:
        conn.execute(f"COPY {table} FROM '{path}' ({options});")
    if SKIP_COUNTS:
        return f"copied_files={len(paths)}"
    if rel:
        count = query_one(conn, f"MATCH ()-[r:{table}]->() RETURN count(*);")[0]
        return f"edges={count}"
    count = query_one(conn, f"MATCH (n:{table}) RETURN count(*);")[0]
    return f"nodes={count}"


def main() -> None:
    if not CSV_DIR.is_dir():
        raise SystemExit(f"Dataset directory not found: {CSV_DIR}")

    print(f"=== Build Kuzu {DATASET} database with Kuzu {kuzu.__version__} ===")
    print(f"CSV_DIR={CSV_DIR}")
    print(f"DB_PATH={DB_PATH}")
    print(
        f"threads={THREADS}, buffer_pool_gib={ARGS.buffer_pool_gib}, "
        f"reuse_staging={REUSE_STAGING}, skip_counts={SKIP_COUNTS}, "
        f"resume_rels={RESUME_RELS}, reset_rels={RESET_RELS}, "
        f"strict_rel_copy={STRICT_REL_COPY}, only_rels={sorted(ONLY_RELS)}, "
        f"skip_rels={sorted(SKIP_RELS)}"
    )
    DB_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    clean_database()
    STAGING.mkdir(parents=True, exist_ok=True)

    print("\n--- 1. Preprocess CSVs ---")
    papers_header = [
        "paperid", "doi", "year", "date", "doctype", "cited_by_count", "is_retracted",
        "reference_count", "citation_count", "C3", "C5", "C10", "disruption",
        "Atyp_Median_Z", "Atyp_10pct_Z", "Atyp_Pairs", "WSB_mu", "WSB_sigma",
        "WSB_Cinf", "SB_B", "SB_T", "team_size", "institution_count", "patent_count",
        "newsfeed_count", "nct_count", "nih_count", "nsf_count",
    ]
    authors_header = [
        "authorid", "avg_c10", "avg_logc10", "productivity", "h_index", "display_name",
        "inference_sources", "inference_counts", "p_gf",
    ]
    author_details_header = [
        "authorid", "orcid", "display_name", "display_name_alternatives", "works_count",
        "cited_by_count", "last_known_institution", "works_api_url", "updated_date",
    ]
    affiliations_header = [
        "institutionid", "display_name", "ror", "homepage_url", "country_code", "type",
        "h_index", "productivity", "avg_c10", "avg_logc10",
    ]
    fields_header = [
        "id", "wikidata", "display_name", "level", "description", "works_count",
        "cited_by_count", "image_url", "image_thumbnail_url", "works_api_url",
        "updated_date", "fieldid",
    ]
    sources_header = ["sourceid", "display_name", "issn", "publisher", "homepage_url", "is_oa"]

    paper_sources = source_files("sciscinet_papers.csv", prefix="sciscinet_papers")
    papers = prepare_direct_or_project(
        "papers",
        paper_sources,
        papers_header,
        (lambda _idx, r: r[1:]) if paper_sources and len(read_header(paper_sources[0])) == len(papers_header) + 1 else None,
    )
    author_sources = source_files("sciscinet_authors.csv")
    authors = prepare_direct_or_project(
        "authors",
        author_sources,
        authors_header,
        (lambda _idx, r: r[1:]) if author_sources and len(read_header(author_sources[0])) == len(authors_header) + 1 else None,
    )
    author_details = prepare_direct_or_project(
        "author_details",
        source_files("sciscinet_author_details.csv"),
        author_details_header,
    )
    affiliation_sources = source_files("sciscinet_affiliations.csv")
    affiliations = prepare_direct_or_project(
        "affiliations",
        affiliation_sources,
        affiliations_header,
        (lambda _idx, r: r[1:]) if affiliation_sources and len(read_header(affiliation_sources[0])) == len(affiliations_header) + 1 else None,
    )
    field_sources = source_files("sciscinet_fields.csv")
    fields = prepare_direct_or_project(
        "fields",
        field_sources,
        fields_header,
        (lambda _idx, r: r[1:]) if field_sources and len(read_header(field_sources[0])) == len(fields_header) + 1 else None,
    )
    sources = prepare_direct_or_project(
        "sources",
        source_files("sciscinet_sources.csv"),
        sources_header,
    )
    paper_details = prepare_direct_or_project(
        "paper_details",
        source_files("sciscinet_paperdetails.csv"),
        [
            "paperid", "doi", "title", "display_name", "year", "date", "doctype",
            "cited_by_count", "is_retracted", "is_paratext", "cited_by_api_url",
            "abstract_inverted_index", "language",
        ],
    )
    twitter_metadata = prepare_direct_or_project(
        "twitter_metadata",
        source_files("sciscinet_twitter_metadata.csv"),
        ["tweet_id", "occurred_time", "doi", "original_tweet_url"],
    )

    rowid_specs = {
        "clinicaltrials_metadata": (
            source_files("sciscinet_clinicaltrials_metadata.csv"),
            ["kpk", "paperid", "nct_id", "pmid", "pmcid", "doi", "reference_type", "citation"],
            None,
        ),
        "hit_papers_level0": (
            source_files("hit_papers_level0.csv"),
            ["kpk", "paperid", "fieldid", "year", "citation_count", "Hit_1pct", "Hit_5pct", "Hit_10pct"],
            None,
        ),
        "hit_papers_level1": (
            source_files("hit_papers_level1.csv", alternatives=("hit_papers_level1_export.csv",)),
            ["kpk", "paperid", "fieldid", "year", "citation_count", "Hit_1pct", "Hit_5pct", "Hit_10pct"],
            None,
        ),
        "link_clinicaltrials": (
            source_files("sciscinet_link_clinicaltrials.csv"),
            ["kpk", "paperid", "nct_id"],
            lambda idx, r: [idx, *r[-2:]],
        ),
        "link_newsfeed": (
            source_files("sciscinet_link_newsfeed.csv"),
            ["kpk", "paperid", "newsfeed_id"],
            lambda idx, r: [idx, *r[-2:]],
        ),
        "link_nih": (
            source_files("sciscinet_link_nih.csv"),
            ["kpk", "paperid", "award_id"],
            lambda idx, r: [idx, *r[-2:]],
        ),
        "link_nobellaureates": (
            source_files("sciscinet_link_nobellaureates.csv", alternatives=("sciscinet_link_nobellaureates_clean.csv",)),
            ["kpk", "paperid", "laureate_id", "type"],
            None,
        ),
        "link_nsf": (
            source_files("sciscinet_link_nsf.csv"),
            ["kpk", "paperid", "award_id"],
            lambda idx, r: [idx, *r[-2:]],
        ),
        "link_patents": (
            source_files("sciscinet_link_patents.csv"),
            ["kpk", "paperid", "patent", "uspto"],
            None,
        ),
        "newsfeed_metadata": (
            source_files("sciscinet_newsfeed_metadata.csv"),
            ["kpk", "paperid", "doi", "subj_id", "newsfeed_id", "timestamp"],
            None,
        ),
        "nih_metadata": (
            source_files("sciscinet_nih_metadata.csv"),
            ["kpk", "paperid", "doi", "type_crossref", "funder_display_name", "award_id", "funderid"],
            None,
        ),
        "normalized_citations_level0": (
            source_files("normalized_citations_level0.csv"),
            ["kpk", "paperid", "fieldid", "year", "citation_count", "c0", "normalized_citations", "level"],
            None,
        ),
        "normalized_citations_level1": (
            source_files("normalized_citations_level1.csv"),
            ["kpk", "paperid", "fieldid", "year", "citation_count", "c0", "normalized_citations", "level"],
            None,
        ),
        "nsf_metadata": (
            source_files("sciscinet_nsf_metadata.csv"),
            ["kpk", "paperid", "doi", "type_crossref", "funder_display_name", "award_id", "funderid"],
            None,
        ),
    }
    rowid_paths = {}
    for name, (srcs, header, builder) in rowid_specs.items():
        if builder is not None and srcs and len(read_header(srcs[0])) != len(header) - 1:
            rowid_paths[name] = project_csvs(name, srcs, header, builder)
        else:
            rowid_paths[name] = prepend_rowid_paths(name, srcs, header)

    paperrefs_sources = source_files("sciscinet_paperrefs.csv", prefix="sciscinet_paperrefs")
    paperrefs = prepare_direct_or_project(
        "paperrefs",
        paperrefs_sources,
        ["citing_paperid", "cited_paperid", "year", "ref_year", "year_diff"],
        (lambda _idx, r: [r[4], r[5], r[6], r[7], r[8]])
        if paperrefs_sources and len(read_header(paperrefs_sources[0])) == 9
        else None,
    )
    authors_paper_sources = source_files("sciscinet_authors_paperid.csv", prefix="sciscinet_authors_paperid")
    papers_to_authors = prepare_direct_or_project(
        "papers_to_authors",
        authors_paper_sources,
        ["paperid", "authorid", "display_name"],
        (lambda _idx, r: [r[6], r[4], r[5]])
        if authors_paper_sources and len(read_header(authors_paper_sources[0])) == 7
        else (lambda _idx, r: [r[2], r[0], r[1]]),
    )
    authors_paper = project_csvs(
        "authors_paper",
        authors_paper_sources,
        ["authorid", "paperid", "display_name"],
        (lambda _idx, r: [r[4], r[6], r[5]])
        if authors_paper_sources and len(read_header(authors_paper_sources[0])) == 7
        else (lambda _idx, r: [r[0], r[2], r[1]]),
    )
    contributed_sources = source_files(
        "sciscinet_paper_author_affiliation.csv",
        prefix="sciscinet_paper_author_affiliation",
    )
    contributed_from = prepare_direct_or_project(
        "contributed_from",
        contributed_sources,
        ["paperid", "institutionid", "author_position", "authorid", "raw_affiliation_string"],
        (lambda _idx, r: [r[4], r[7], r[5], r[6], r[8]])
        if contributed_sources and len(read_header(contributed_sources[0])) == 9
        else (lambda _idx, r: [r[0], r[3], r[1], r[2], r[4]]),
    )
    affl_sources = source_files("sciscinet_affl_assoc_affl.csv")
    affl_assoc = prepare_direct_or_project(
        "affl_assoc_affl",
        affl_sources,
        ["institutionid", "associated_institution_id", "relationship"],
        (lambda _idx, r: [r[4], r[5], r[6]])
        if affl_sources and len(read_header(affl_sources[0])) == 7
        else None,
    )
    author_affiliation_sources = source_files("sciscinet_author_affiliation.csv", prefix="sciscinet_author_affiliation")
    affiliated_with = prepare_direct_or_project(
        "affiliated_with",
        author_affiliation_sources,
        ["authorid", "institutionid", "author_position"],
        (lambda _idx, r: [r[6], r[4], r[5]])
        if author_affiliation_sources and len(read_header(author_affiliation_sources[0])) == 7
        else (lambda _idx, r: [r[2], r[0], r[1]]),
    )
    paperfields_sources = source_files("sciscinet_paperfields.csv", prefix="sciscinet_paperfields")
    paperfields = prepare_direct_or_project(
        "paperfields",
        paperfields_sources,
        ["paperid", "fieldid", "score_openalex"],
        (lambda _idx, r: [r[4], r[5], r[6]])
        if paperfields_sources and len(read_header(paperfields_sources[0])) == 7
        else None,
    )
    link_twitter_rel = prepare_direct_or_project(
        "link_twitter_rel",
        source_files("sciscinet_link_twitter.csv"),
        ["paperid", "tweet_id"],
        lambda _idx, r: r[-2:],
    )
    papersources = prepare_direct_or_project(
        "papersources",
        source_files("sciscinet_papersources.csv", prefix="sciscinet_papersources"),
        ["paperid", "sourceid", "landing_page_url", "pdf_url", "is_oa", "version", "license"],
    )

    print("\n--- 2. Create schema ---")
    db_kwargs = {}
    if BUFFER_POOL_BYTES > 0:
        db_kwargs["buffer_pool_size"] = BUFFER_POOL_BYTES
    if THREADS > 0:
        db_kwargs["max_num_threads"] = THREADS
    db = kuzu.Database(str(DB_PATH), **db_kwargs)
    conn = kuzu.Connection(db, num_threads=THREADS)

    ddl = [
        """
        CREATE NODE TABLE Papers(
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
        CREATE NODE TABLE Authors_Gender(
            authorid STRING PRIMARY KEY, avg_c10 STRING, avg_logc10 STRING,
            productivity INT64, h_index INT64, display_name STRING,
            inference_sources INT64, inference_counts INT64, p_gf STRING
        );
        """,
        """
        CREATE NODE TABLE AuthorDetails(
            authorid STRING PRIMARY KEY, orcid STRING, display_name STRING,
            display_name_alternatives STRING, works_count STRING, cited_by_count STRING,
            last_known_institution STRING, works_api_url STRING, updated_date STRING
        );
        """,
        """
        CREATE NODE TABLE Affiliations(
            institutionid STRING PRIMARY KEY, display_name STRING, ror STRING,
            homepage_url STRING, country_code STRING, type STRING,
            h_index STRING, productivity STRING, avg_c10 STRING, avg_logc10 STRING
        );
        """,
        """
        CREATE NODE TABLE Fields(
            id STRING, wikidata STRING, display_name STRING, level INT64,
            description STRING, works_count INT64, cited_by_count INT64,
            image_url STRING, image_thumbnail_url STRING, works_api_url STRING,
            updated_date STRING, fieldid STRING PRIMARY KEY
        );
        """,
        """
        CREATE NODE TABLE Sources(
            sourceid STRING PRIMARY KEY, display_name STRING, issn STRING,
            publisher STRING, homepage_url STRING, is_oa STRING
        );
        """,
        """
        CREATE NODE TABLE PaperDetails(
            paperid STRING PRIMARY KEY, doi STRING, title STRING, display_name STRING,
            year INT64, date STRING, doctype STRING, cited_by_count INT64,
            is_retracted STRING, is_paratext STRING, cited_by_api_url STRING,
            abstract_inverted_index STRING, language STRING
        );
        """,
        """
        CREATE NODE TABLE Twitter_Metadata(
            tweet_id STRING PRIMARY KEY, occurred_time STRING, doi STRING,
            original_tweet_url STRING
        );
        """,
        """
        CREATE NODE TABLE clinicaltrials_metadata(
            kpk INT64 PRIMARY KEY, paperid STRING, nct_id STRING, pmid INT64,
            pmcid INT64, doi STRING, reference_type STRING, citation STRING
        );
        """,
        """
        CREATE NODE TABLE hit_papers_level0(
            kpk INT64 PRIMARY KEY, paperid STRING, fieldid STRING, year INT64,
            citation_count INT64, Hit_1pct INT64, Hit_5pct INT64, Hit_10pct INT64
        );
        """,
        """
        CREATE NODE TABLE hit_papers_level1(
            kpk INT64 PRIMARY KEY, paperid STRING, fieldid STRING, year INT64,
            citation_count INT64, Hit_1pct INT64, Hit_5pct INT64, Hit_10pct INT64
        );
        """,
        "CREATE NODE TABLE link_clinicaltrials(kpk INT64 PRIMARY KEY, paperid STRING, nct_id STRING);",
        "CREATE NODE TABLE link_newsfeed(kpk INT64 PRIMARY KEY, paperid STRING, newsfeed_id STRING);",
        "CREATE NODE TABLE link_nih(kpk INT64 PRIMARY KEY, paperid STRING, award_id STRING);",
        "CREATE NODE TABLE link_nobellaureates(kpk INT64 PRIMARY KEY, paperid STRING, laureate_id INT64, type INT64);",
        "CREATE NODE TABLE link_nsf(kpk INT64 PRIMARY KEY, paperid STRING, award_id STRING);",
        "CREATE NODE TABLE link_patents(kpk INT64 PRIMARY KEY, paperid STRING, patent STRING, uspto INT64);",
        """
        CREATE NODE TABLE newsfeed_metadata(
            kpk INT64 PRIMARY KEY, paperid STRING, doi STRING, subj_id STRING,
            newsfeed_id STRING, timestamp STRING
        );
        """,
        """
        CREATE NODE TABLE nih_metadata(
            kpk INT64 PRIMARY KEY, paperid STRING, doi STRING, type_crossref STRING,
            funder_display_name STRING, award_id STRING, funderid STRING
        );
        """,
        """
        CREATE NODE TABLE normalized_citations_level0(
            kpk INT64 PRIMARY KEY, paperid STRING, fieldid STRING, year INT64,
            citation_count STRING, c0 STRING, normalized_citations STRING, level INT64
        );
        """,
        """
        CREATE NODE TABLE normalized_citations_level1(
            kpk INT64 PRIMARY KEY, paperid STRING, fieldid STRING, year INT64,
            citation_count STRING, c0 STRING, normalized_citations STRING, level INT64
        );
        """,
        """
        CREATE NODE TABLE nsf_metadata(
            kpk INT64 PRIMARY KEY, paperid STRING, doi STRING, type_crossref STRING,
            funder_display_name STRING, award_id STRING, funderid STRING
        );
        """,
        """
        CREATE NODE TABLE Papers_test(
            paperid STRING PRIMARY KEY, title STRING, year INT64, citation_count INT64
        );
        """,
        """
        CREATE NODE TABLE Authors_test(
            authorid STRING PRIMARY KEY, display_name STRING, gender STRING, affiliation STRING
        );
        """,
        "CREATE REL TABLE PaperReferences(FROM Papers TO Papers, year INT64, ref_year INT64, year_diff INT64);",
        "CREATE REL TABLE Papers_to_Authors(FROM Papers TO Authors_Gender, display_name STRING);",
        "CREATE REL TABLE Authors_Paper(FROM Authors_Gender TO Papers, display_name STRING);",
        """
        CREATE REL TABLE contributed_from(
            FROM Papers TO Affiliations, author_position STRING,
            authorid STRING, raw_affiliation_string STRING
        );
        """,
        "CREATE REL TABLE affl_assoc_affl(FROM Affiliations TO Affiliations, relationship STRING);",
        "CREATE REL TABLE affiliated_with(FROM Authors_Gender TO Affiliations, author_position STRING);",
        "CREATE REL TABLE PaperFields(FROM Papers TO Fields, score_openalex STRING);",
        "CREATE REL TABLE link_twitter(FROM Papers TO Twitter_Metadata);",
        """
        CREATE REL TABLE papersources(
            FROM Papers TO Sources, landing_page_url STRING, pdf_url STRING,
            is_oa STRING, version STRING, license STRING
        );
        """,
        "CREATE REL TABLE cited(FROM Papers TO Papers);",
        "CREATE REL TABLE knows(FROM Authors_Gender TO Authors_Gender, FROM Authors_test TO Authors_test);",
    ]
    for statement in ddl:
        if not RESUME_RELS:
            timed("create table", lambda s=statement: conn.execute(s))

    rel_table_names = [
        "PaperReferences",
        "Papers_to_Authors",
        "Authors_Paper",
        "contributed_from",
        "affl_assoc_affl",
        "affiliated_with",
        "PaperFields",
        "link_twitter",
        "papersources",
        "cited",
        "knows",
    ]
    rel_ddl = ddl[-len(rel_table_names):]
    if RESUME_RELS and RESET_RELS:
        for table in rel_table_names:
            timed(f"drop {table}", lambda t=table: conn.execute(f"DROP TABLE IF EXISTS {t};"))
        for statement in rel_ddl:
            timed("create rel table", lambda s=statement: conn.execute(s))

    print("\n--- 3. Copy data ---")
    node_loads = [
        ("Papers", papers),
        ("Authors_Gender", authors),
        ("AuthorDetails", author_details),
        ("Affiliations", affiliations),
        ("Fields", fields),
        ("Sources", sources),
        ("PaperDetails", paper_details),
        ("Twitter_Metadata", twitter_metadata),
        *rowid_paths.items(),
    ]
    if not RESUME_RELS:
        for table, path in node_loads:
            timed(f"load {table}", lambda t=table, p=path: copy_table(conn, t, p))

    rel_loads = [
        ("PaperReferences", paperrefs),
        ("Papers_to_Authors", papers_to_authors),
        ("Authors_Paper", authors_paper),
        ("contributed_from", contributed_from),
        ("affl_assoc_affl", affl_assoc),
        ("affiliated_with", affiliated_with),
        ("PaperFields", paperfields),
        ("link_twitter", link_twitter_rel),
        ("papersources", papersources),
    ]
    for table, path in rel_loads:
        if ONLY_RELS and table not in ONLY_RELS:
            print(f"{'skip ' + table:48s} {'0.00s':>9s}  not in --only-rels", flush=True)
            continue
        if table in SKIP_RELS:
            print(f"{'skip ' + table:48s} {'0.00s':>9s}  listed in --skip-rels", flush=True)
            continue
        timed(f"load {table}", lambda t=table, p=path: copy_table(conn, t, p, rel=True))

    print("\n--- 4. Sanity probes ---")
    probes = ["MATCH (p:Papers) WHERE p.paperid = 'W2122344208' RETURN p.paperid;"]
    if not SKIP_COUNTS:
        probes.extend(
            [
                "MATCH (p:Papers)-[:PaperReferences]->(q:Papers) RETURN count(*);",
                "MATCH (p:Papers)-[:Papers_to_Authors]->(a:Authors_Gender) RETURN count(*);",
            ]
        )
    for probe in probes:
        print(f"{probe} -> {query_one(conn, probe)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
