#!/usr/bin/env python3
"""Fail-closed static audit for the OrientDB GRBench query suite."""

from __future__ import annotations

import argparse
import csv
import inspect
import re
import sys
from pathlib import Path
from typing import List, Sequence, Set

TOOL_DIR = Path(__file__).resolve().parent
RUNNERS_DIR = TOOL_DIR.parent
ADAPTER_DIR = RUNNERS_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
sys.path.insert(0, str(RUNNERS_DIR))
import run_orientdb
from run_orientdb import CATEGORIES, class_names_from_schema


ROOT = ADAPTER_DIR
DEFAULT_SOURCE_ROOT = REPO_ROOT / "benchmark" / "queries" / "canonical"
DEFAULT_QUERY_ROOT = ADAPTER_DIR / "queries"
PURE_JOIN_VARIANT_MANIFEST = REPO_ROOT / "benchmark" / "manifests" / "pure_join_variants.csv"
MAIN_CATEGORIES = (
    "High_Join_Relational_Graph_Hybrid_Queries",
    "Low_Join_Relational_Graph_Hybrid_Queries",
    "Pure_Graph_Queries",
)


def sql_files(root: Path) -> Set[str]:
    paths = set()
    for category in CATEGORIES:
        category_root = root / category
        if not category_root.exists():
            continue
        paths.update(str(path.relative_to(root)) for path in category_root.rglob("*.sql"))
    return paths


def audit_pure_join_variants(query_root: Path, failures: List[str]) -> None:
    """Validate the separately executable Pure Join physical variants."""
    if not PURE_JOIN_VARIANT_MANIFEST.is_file():
        failures.append(f"missing Pure Join variant manifest: {PURE_JOIN_VARIANT_MANIFEST}")
        return

    with PURE_JOIN_VARIANT_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    expected = {}
    for category in MAIN_CATEGORIES:
        for path in sorted((query_root / category).rglob("*.sql")):
            query_id = path.stem
            expected[f"pure_join/{query_id}"] = (
                f"main/{query_id}",
                "benchmark/queries/canonical/Pure_Join_Queries/"
                f"{path.relative_to(query_root).as_posix()}",
            )

    actual = {row.get("variant_id", ""): row for row in rows}
    if len(rows) != 96 or len(actual) != 96:
        failures.append(
            "Pure Join variant manifest must contain 96 unique rows: "
            f"rows={len(rows)},unique={len(actual)}"
        )
    if set(actual) != set(expected):
        failures.append(
            "Pure Join variant IDs do not match the 96 native main queries: "
            f"missing={sorted(set(expected) - set(actual))},"
            f"extra={sorted(set(actual) - set(expected))}"
        )

    for variant_id, (logical_id, canonical_path) in expected.items():
        row = actual.get(variant_id)
        if row is None:
            continue
        if row.get("logical_query_id") != logical_id:
            failures.append(f"incorrect logical mapping for {variant_id}")
        if row.get("canonical_path") != canonical_path:
            failures.append(f"incorrect canonical path for {variant_id}")
        if row.get("status") != "physical_variant":
            failures.append(f"incorrect variant status for {variant_id}")

    variant_root = query_root / "Pure_Join_Queries"
    variant_files = list(variant_root.rglob("*.sql")) if variant_root.exists() else []
    if len(variant_files) != 96:
        failures.append(
            f"OrientDB must publish 96 executable Pure Join variants: found={len(variant_files)}"
        )


def audit_optional_scalar_aggregate(path: Path, failures: List[str]) -> None:
    """Check the OrientDB form equivalent to canonical LEFT JOIN aggregates."""
    sql = path.read_text(errors="replace")
    required = (
        "$q0 = (SELECT MIN(p3) AS v",
        "$q1 = (SELECT MIN(author) AS v",
        "$q2 = (SELECT MIN(newsfeed) AS v",
        "$q0[0].v AS min_ref_paperid",
        "$q1[0].v AS author",
        "$q2[0].v AS newsfeed",
    )
    for fragment in required:
        if fragment not in sql:
            failures.append(f"optional scalar aggregate is incomplete: {path}: {fragment}")

    sections = sql.split("LET", 1)[-1]
    q0 = sections.split("$q0 =", 1)[-1].split("$q1 =", 1)[0]
    q1 = sections.split("$q1 =", 1)[-1].split("$q2 =", 1)[0]
    q2 = sections.split("$q2 =", 1)[-1]
    main_path = ".out('PaperReferences')"
    if any(section.count(main_path) != 3 for section in (q0, q1, q2)):
        failures.append(f"optional scalar aggregates do not share the three-hop main path: {path}")
    if "Authors_Paper" in q0 or "link_newsfeed" in q0:
        failures.append(f"optional branches filter the main-path aggregate: {path}")
    if ".in('Authors_Paper')" not in q1 or "link_newsfeed" in q1:
        failures.append(f"author scalar aggregate has incorrect branch isolation: {path}")
    if ".out('link_newsfeed')" not in q2 or "Authors_Paper" in q2:
        failures.append(f"newsfeed scalar aggregate has incorrect branch isolation: {path}")


def require_contains(path: Path, fragments: Sequence[str], failures: List[str]) -> None:
    sql = path.read_text(errors="replace")
    for fragment in fragments:
        if fragment not in sql:
            failures.append(f"{path}: missing required fragment: {fragment}")


def audit(source_root: Path, query_root: Path) -> List[str]:
    failures: List[str] = []
    source_paths = sql_files(source_root)
    query_paths = sql_files(query_root)
    for missing in sorted(source_paths - query_paths):
        failures.append(f"missing OrientDB query: {missing}")
    for extra in sorted(query_paths - source_paths):
        failures.append(f"extra OrientDB query: {extra}")

    class_names_from_schema()
    audit_pure_join_variants(query_root, failures)

    all_sql = "\n".join(path.read_text(errors="replace") for path in query_root.rglob("*.sql"))
    forbidden_patterns = {
        "NIH paperid-to-paperid metadata join": r"Link_NIH\s+WHERE\s+paperid\s+IN\s*\(SELECT\s+paperid\s+FROM\s+NIH_Metadata",
        "NSF paperid-to-paperid metadata join": r"Link_NSF\s+WHERE\s+paperid\s+IN\s*\(SELECT\s+paperid\s+FROM\s+NSF_Metadata",
    }
    for description, pattern in forbidden_patterns.items():
        if re.search(pattern, all_sql, flags=re.IGNORECASE):
            failures.append(f"forbidden pattern remains: {description}")

    update_root = query_root / "update" / "Update"
    expected_update_files = {f"{number}{suffix}.sql" for number in range(1, 7) for suffix in ("a", "b")}
    batch_update_files = set(getattr(run_orientdb, "UPDATE_BATCH_OPERATIONS", {}))
    if batch_update_files != expected_update_files:
        failures.append(
            "native batched Update mapping mismatch: "
            f"expected={sorted(expected_update_files)},actual={sorted(batch_update_files)}"
        )
    if getattr(run_orientdb, "WORKER_PROTOCOL_VERSION", "") != "4":
        failures.append("benchmark worker protocol is not the audited native Update v4 protocol")
    if getattr(run_orientdb, "WORKER_STARTUP_TIMEOUT_S", 0) != 18000:
        failures.append("worker startup timeout does not allow large-SF WAL recovery")
    expected_scale_factors = ["sf10_0", "sf10_1", "sf10_2", "sf10_3", "sf10_4"]
    if getattr(run_orientdb, "SCALE_FACTORS", []) != expected_scale_factors:
        failures.append(
            "benchmark scale-factor coverage mismatch: "
            f"expected={expected_scale_factors},actual={getattr(run_orientdb, 'SCALE_FACTORS', [])}"
        )
    for update6_file in ("6a.sql", "6b.sql"):
        if "Authors_Paper" not in run_orientdb.UPDATE_AFFECTED_CLASSES.get(update6_file, []):
            failures.append(f"{update6_file} does not verify preserved Authors_Paper cardinality")
    if getattr(run_orientdb, "UPDATE6_AUTHOR_SHADOW", "") != "_GrbenchUpdate6AuthorShadow":
        failures.append("Update 6 author-shadow support class is missing")
    if (
        getattr(run_orientdb, "UPDATE_RECOVERY_PROGRESS", "")
        != "_GrbenchUpdateRecoveryProgress"
    ):
        failures.append("resumable Update recovery-progress support class is missing")
    if getattr(run_orientdb, "DEFAULT_UPDATE_RECOVERY_MAX_ATTEMPTS", 0) != 12:
        failures.append("Update recovery retry budget is not the audited 12 attempts")
    update_runner_source = inspect.getsource(run_orientdb.run_update_query_file_warm)
    update_runner_parameters = inspect.signature(
        run_orientdb.run_update_query_file_warm
    ).parameters
    for recovery_parameter in (
        "recovery_timeout_s",
        "recovery_max_attempts",
    ):
        if recovery_parameter not in update_runner_parameters:
            failures.append(
                f"Update runner is missing independent recovery parameter {recovery_parameter}"
            )
    for recovery_metadata_fragment in (
        '"update_recovery_timeout_seconds": recovery_timeout_s',
        '"update_recovery_max_attempts": recovery_max_attempts',
        "max_attempts=recovery_max_attempts",
    ):
        if recovery_metadata_fragment not in update_runner_source:
            failures.append(
                "Update runner is missing recovery wiring: "
                f"{recovery_metadata_fragment}"
            )
    if re.search(r'run_statements\(\[\s*["\']BEGIN["\']', update_runner_source):
        failures.append("Update runner still wraps the complete workload in one transaction")
    preflight_source = inspect.getsource(run_orientdb.database_preflight)
    for support_constant in ("UPDATE6_AUTHOR_SHADOW", "UPDATE_RECOVERY_PROGRESS"):
        if support_constant not in preflight_source:
            failures.append(
                f"database preflight does not require empty support class {support_constant}"
            )

    recovery_source = inspect.getsource(run_orientdb.recover_and_verify_update_baseline)
    for recovery_fragment in (
        "progress_count > 0",
        'recovery_mode = "RESTORE_ONLY"',
        "finalize_and_verify_recovery_progress",
    ):
        if recovery_fragment not in recovery_source:
            failures.append(
                f"runner is missing resumable recovery logic: {recovery_fragment}"
            )

    runner_source = Path(run_orientdb.__file__).read_text(errors="replace")
    for recovery_cli_fragment in (
        '"--update-recovery-timeout"',
        '"--update-recovery-max-attempts"',
        "recovery_timeout_s=args.update_recovery_timeout",
        "recovery_max_attempts=args.update_recovery_max_attempts",
        '"update_recovery_timeout_seconds": args.update_recovery_timeout',
        '"update_recovery_max_attempts": args.update_recovery_max_attempts',
    ):
        if recovery_cli_fragment not in runner_source:
            failures.append(
                f"runner is missing recovery CLI/metadata wiring: {recovery_cli_fragment}"
            )

    loader_source = (ADAPTER_DIR / "loaders" / "OrientDbCsvLoader.java").read_text(
        errors="replace"
    )
    for prefix_resume_fragment in (
        "resumePartialEdgePrefixes",
        "RESUME committed source-prefix edge",
        "committed_source_prefix_append",
        "one_source_row_per_existing_edge_and_zero_prior_skips",
        "compatibleLoaderConfigSha256s",
    ):
        if prefix_resume_fragment not in loader_source:
            failures.append(
                f"loader is missing audited partial-edge prefix resume wiring: {prefix_resume_fragment}"
            )

    worker_source = run_orientdb.WORKER_SOURCE.read_text(errors="replace")
    for required_worker_fragment in (
        "_GrbenchUpdate6AuthorShadow",
        "_GrbenchUpdateRecoveryProgress",
        "ensureUpdateSupportSchema",
        "findIndexedElement",
        "moveAuthors",
        "restoreSpecResumable",
        "database.browseCluster(",
        "database.getLocalCache().clear()",
        '"RESTORE_ONLY".equals(mode)',
        '"FINALIZE_RECOVERY".equals(mode)',
        '"6a.sql".equals(filename)',
        '"6b.sql".equals(restoreFile)',
    ):
        if required_worker_fragment not in worker_source:
            failures.append(
                f"native worker missing Update 6 preservation logic: {required_worker_fragment}"
            )
    if "allowExisting && findTarget" in worker_source:
        failures.append("recovery still collapses duplicate staging rows by target-key lookup")
    if 'query.append(" WHERE @rid > ?")' in worker_source:
        failures.append("recovery still rescans staging classes with SQL RID predicates")

    for insert_path in sorted(update_root.glob("*b.sql")):
        sql = insert_path.read_text(errors="replace")
        if re.search(r"INSERT\s+INTO\s+\w+\s+SELECT", sql, flags=re.IGNORECASE):
            failures.append(f"unsupported INSERT SELECT remains: {insert_path}")
        if "RETURN " not in sql:
            failures.append(f"bulk Update does not suppress record output: {insert_path}")

    require_contains(
        update_root / "1a.sql",
        [
            "DELETE EDGE PaperReferences",
            "DELETE EDGE Papers_to_Authors",
            "DELETE EDGE Authors_Paper",
            "DELETE EDGE contributed_from",
            "DELETE EDGE PaperFields",
            "DELETE EDGE Link_NSF",
            "DELETE EDGE Link_NIH",
            "DELETE EDGE Link_ClinicalTrials",
            "DELETE EDGE link_newsfeed",
            "DELETE EDGE link_twitter",
        ],
        failures,
    )
    require_contains(
        update_root / "1b.sql",
        [
            "SELECT FROM grbench_update3_paperreferences",
            "SELECT FROM grbench_update3_authors_paper",
            "SELECT FROM _MissingEndpoint",
        ],
        failures,
    )
    require_contains(
        update_root / "2b.sql",
        [
            "year = $e.year",
            "ref_year = $e.ref_year",
            "year_diff = $e.year_diff",
            "SELECT FROM _MissingEndpoint",
        ],
        failures,
    )
    require_contains(
        update_root / "3a.sql",
        ["DELETE EDGE Authors_Paper"],
        failures,
    )
    require_contains(
        update_root / "3b.sql",
        [
            "SELECT FROM grbench_update1_papers_to_authors",
            "year = $e.year",
            "ref_year = $e.ref_year",
            "year_diff = $e.year_diff",
            "institutionid = $e.institution_id",
            "institution_id = $e.institution_id",
            "authorid = $e.authorid",
            "score_openalex = $e.score_openalex",
            "SELECT FROM _MissingEndpoint",
        ],
        failures,
    )
    require_contains(
        update_root / "4a.sql",
        [
            "DELETE EDGE Papers_to_Authors",
            "DELETE EDGE Authors_Paper",
            "DELETE EDGE affiliated_with",
        ],
        failures,
    )
    require_contains(
        update_root / "5a.sql",
        [
            "paperid = $e.paperid",
            "authorid = $e.authorid",
        ],
        failures,
    )
    require_contains(
        update_root / "4b.sql",
        [
            "SELECT FROM grbench_update6_papers_to_authors",
            "SELECT FROM grbench_update4_authors_paper",
            "SELECT FROM grbench_update6_affiliated_with",
            "SELECT FROM _MissingEndpoint",
        ],
        failures,
    )
    for restore_name in ("5b.sql", "6b.sql"):
        require_contains(
            update_root / restore_name,
            ["SELECT FROM _MissingEndpoint"],
            failures,
        )

    for suffix in ("12a.sql", "12b.sql", "12c.sql"):
        path = (
            query_root
            / "High_Join_Relational_Graph_Hybrid_Queries"
            / "High-Join Single-Subgraph Single-Hop"
            / suffix
        )
        sql = path.read_text(errors="replace")
        hit_section = sql.split("$q2 =", 1)[-1].split("$q3 =", 1)[0]
        if "WHERE paperid IN" not in hit_section:
            failures.append(f"unrestricted hit_papers_level1 aggregate: {path}")

    for suffix in ("32a.sql", "32b.sql", "32c.sql"):
        path = query_root / "Pure_Graph_Queries" / suffix
        audit_optional_scalar_aggregate(path, failures)

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--query-root", type=Path, default=DEFAULT_QUERY_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures = audit(args.source_root, args.query_root)
    if failures:
        print(f"FAIL: {len(failures)} contract violation(s)")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: query coverage and static semantic contract checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
