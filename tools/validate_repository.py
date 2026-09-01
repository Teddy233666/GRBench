#!/usr/bin/env python3
"""Validate GRBench's public repository contract without opening a database."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from audit_query_semantics import audit as audit_query_semantics


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "benchmark" / "queries" / "canonical"
MANIFESTS = ROOT / "benchmark" / "manifests"
RESULT_MANIFEST = ROOT / "results" / "manifests" / "published_results.csv"
EXPECTED_SUITES = {"main": 96, "pure_join": 96, "shortest_path": 15, "update": 12}
EXPECTED_COVERAGE = {
    "agensgraph": Counter({"static_adapter": 207, "legacy_adapter": 12}),
    "arangodb": Counter({"static_adapter": 183, "legacy_unverified": 24, "not_implemented": 12}),
    "duckdb": Counter({"static_adapter": 219}),
    "graindb": Counter({"static_adapter": 204, "not_implemented": 15}),
    "kuzu": Counter({"static_adapter": 123, "duplicate_not_executed": 96}),
    "orientdb": Counter({"static_adapter": 219}),
    "postgresql": Counter({"static_adapter": 192, "not_implemented": 27}),
}
TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".js", ".json", ".md",
    ".py", ".sh", ".sql", ".cypher", ".toml", ".csv", ".tsv", ".txt", ".yaml", ".yml", ".cff",
}
ABSOLUTE_PATH_ALLOWLIST = (
    "tools/sanitize_result_paths.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path, *, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def tracked_or_worktree_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        check=True,
        capture_output=True,
    )
    return sorted({ROOT / line for line in completed.stdout.splitlines() if line})


def validate_queries(errors: list[str]) -> None:
    manifest = rows(MANIFESTS / "query_manifest.csv")
    counts = Counter(row["suite"] for row in manifest)
    check(counts == Counter(EXPECTED_SUITES), f"query suite counts differ: {counts}", errors)
    check(len({row["query_id"] for row in manifest}) == 219, "query IDs are not unique", errors)
    for row in manifest:
        path = ROOT / row["canonical_path"]
        check(path.is_file(), f"missing canonical query: {path.relative_to(ROOT)}", errors)
        if path.is_file():
            check(sha256(path) == row["sha256"], f"stale query hash: {path.relative_to(ROOT)}", errors)

    update_names = sorted(path.name for path in (CANONICAL / "update" / "Update").glob("*.sql"))
    check(update_names == [f"{n}{s}.sql" for n in range(1, 7) for s in "ab"], "canonical Update IDs must be 1a..6b", errors)
    check(not list((CANONICAL / "update").rglob("*c.sql")), "legacy c Update leaked into canonical", errors)

    pure_join_names = sorted(path.name for path in (CANONICAL / "Pure_Join_Queries").rglob("*.sql"))
    check(
        pure_join_names == sorted(f"{number}{suffix}.sql" for number in range(1, 33) for suffix in "abc"),
        "canonical Pure Join IDs must be 1a..32c",
        errors,
    )
    variants = rows(MANIFESTS / "pure_join_variants.csv")
    check(len(variants) == 96, "Pure Join variant manifest must contain 96 rows", errors)
    check(
        {row["variant_id"] for row in variants}
        == {f"pure_join/{number}{suffix}" for number in range(1, 33) for suffix in "abc"},
        "Pure Join variant IDs are incomplete",
        errors,
    )
    for row in variants:
        check(row["logical_query_id"] == row["variant_id"].replace("pure_join/", "main/"), f"incorrect Pure Join logical mapping: {row['variant_id']}", errors)
        check(row["status"] == "physical_variant", f"incorrect Pure Join status: {row['variant_id']}", errors)

    check(
        not (ROOT / "adapters" / "kuzu" / "queries" / "Pure_Join_Queries").exists(),
        "Kuzu must not publish byte-identical Pure Join copies",
        errors,
    )


def validate_duckdb_query_mirror(errors: list[str]) -> None:
    duckdb_root = ROOT / "adapters" / "duckdb" / "queries"
    canonical = {
        (
            Path("Update") / path.name
            if path.relative_to(CANONICAL).parts[0] == "update"
            else path.relative_to(CANONICAL)
        ): path
        for path in CANONICAL.rglob("*.sql")
    }
    mirrored = {
        path.relative_to(duckdb_root): path
        for path in duckdb_root.rglob("*.sql")
    }
    check(set(mirrored) == set(canonical), "DuckDB query mirror paths differ from canonical", errors)
    for rel in sorted(set(canonical) & set(mirrored)):
        check(
            canonical[rel].read_bytes() == mirrored[rel].read_bytes(),
            f"DuckDB query mirror differs from canonical: {rel}",
            errors,
        )


def validate_known_semantics(errors: list[str]) -> None:
    constraints = {
        "Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/16b.sql": ["citation_count<80", "g_ref.paperid  = ln.paperid"],
        "Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/18b.sql": ["citation_count < 80", "LEFT JOIN link_nobellaureates"],
        "Pure_Graph_Queries/26c.sql": ["citation_count =1"],
        "Pure_Graph_Queries/29c.sql": ["m2.h_index  >= 1500"],
        "Pure_Graph_Queries/32a.sql": ["LEFT JOIN GRAPH_TABLE"],
        "Pure_Graph_Queries/32b.sql": ["LEFT JOIN GRAPH_TABLE"],
        "Pure_Graph_Queries/32c.sql": ["LEFT JOIN GRAPH_TABLE"],
    }
    for rel, needles in constraints.items():
        text = (CANONICAL / rel).read_text(encoding="utf-8")
        for needle in needles:
            check(needle in text, f"semantic constraint missing from {rel}: {needle}", errors)

    agens16 = (
        ROOT
        / "adapters/agensgraph/queries/Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/16b.sql"
    ).read_text()
    check("g_ref.paperid)::text" in agens16 and "g_ref.ref_paperid)::text" not in agens16.split("LEFT JOIN link_nobellaureates", 1)[1], "AgensGraph 16b Nobel endpoint regressed", errors)
    arango18 = (
        ROOT
        / "adapters/arangodb/queries/Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/18b.js"
    ).read_text()
    check("hasRows" in arango18 and "FOR nf IN" not in arango18, "ArangoDB 18b optional join regressed", errors)


def validate_coverage(errors: list[str]) -> None:
    coverage = rows(MANIFESTS / "adapter_coverage.csv")
    check(len(coverage) == 7 * 219, "adapter coverage must contain 1533 rows", errors)
    by_adapter: dict[str, Counter[str]] = {}
    for row in coverage:
        by_adapter.setdefault(row["adapter"], Counter())[row["status"]] += 1
        if row["status"] in {"static_adapter", "legacy_adapter", "legacy_unverified", "runtime_generated", "canonical_sql"}:
            check((ROOT / row["adapter_path"]).is_file(), f"coverage path missing: {row['adapter_path']}", errors)
    check(by_adapter == EXPECTED_COVERAGE, f"adapter coverage differs: {by_adapter}", errors)


def validate_data_and_updates(errors: list[str]) -> None:
    data = rows(MANIFESTS / "data_profile.csv")
    check(len(data) == 30, f"canonical_full_v1 must contain 30 unique CSVs, found {len(data)}", errors)
    check(len({row["source_csv"] for row in data}) == 30, "data profile contains duplicate CSV rows", errors)
    required = {"sciscinet_paperdetails.csv", "sciscinet_twitter_metadata.csv"}
    check(required <= {row["source_csv"] for row in data}, "full profile omits PaperDetails or Twitter metadata", errors)

    lifecycle = rows(MANIFESTS / "update_lifecycle.csv")
    check(len(lifecycle) == 12, "Update lifecycle must contain 12 rows", errors)
    for row in lifecycle:
        suffix = Path(row["sql_file"]).stem[-1]
        if suffix == "a":
            check(row["unmeasured_compensation"].endswith("b.sql"), f"missing compensation for {row['sql_file']}", errors)
        else:
            check(row["unmeasured_setup"].endswith("a.sql"), f"missing setup for {row['sql_file']}", errors)

    agens_update = ROOT / "adapters" / "agensgraph" / "queries" / "Update"
    expected_names = {f"{number}{suffix}.sql" for number in range(1, 7) for suffix in "ab"}
    actual_names = {path.name for path in agens_update.glob("*.sql")}
    check(
        actual_names == expected_names,
        f"AgensGraph Update files must be exactly 1a..6b: {sorted(actual_names)}",
        errors,
    )

    kuzu_update = ROOT / "adapters" / "kuzu" / "queries" / "Update"
    expected_kuzu_names = {f"{number}{suffix}.cypher" for number in range(1, 7) for suffix in "ab"}
    actual_kuzu_names = {path.name for path in kuzu_update.glob("*.cypher")}
    check(
        actual_kuzu_names == expected_kuzu_names,
        f"Kuzu Update files must be exactly 1a..6b: {sorted(actual_kuzu_names)}",
        errors,
    )
    try:
        kuzu_manifest = json.loads((kuzu_update / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        errors.append(f"Kuzu Update manifest is unreadable: {exc}")
        kuzu_manifest = []
    expected_kuzu_ids = [f"{number}{suffix}" for number in range(1, 7) for suffix in "ab"]
    check(
        [entry.get("query_id") for entry in kuzu_manifest if isinstance(entry, dict)] == expected_kuzu_ids,
        "Kuzu Update manifest IDs must be ordered 1a..6b",
        errors,
    )
    for entry in kuzu_manifest:
        if not isinstance(entry, dict):
            errors.append("Kuzu Update manifest entries must be objects")
            continue
        query_id = entry.get("query_id", "")
        template = entry.get("template", "")
        check(
            isinstance(template, str) and (kuzu_update / template).is_file(),
            f"Kuzu Update template missing for {query_id}: {template}",
            errors,
        )
        expected_setup = f"{query_id[0]}a" if isinstance(query_id, str) and query_id.endswith("b") else None
        check(
            entry.get("setup_query") == expected_setup,
            f"Kuzu Update setup mapping differs for {query_id}",
            errors,
        )


def validate_workflow_layout(errors: list[str]) -> None:
    required = [
        "data/raw/README.md",
        "data/processed/README.md",
        "data/schema/sciscinet.py",
        "scripts/data_generation/sciscinet/csv_generator.py",
        "scripts/data_generation/sciscinet/interface.py",
        "scripts/data_generation/derive_update_staging.sql",
        "scripts/data_generation/validate_data_profile.py",
        "scripts/render_loader.py",
        "docs/data-preparation.md",
        "docs/database-loading.md",
        "docs/benchmark-execution.md",
        "docs/repository-layout.md",
        "adapters/kuzu/loaders/load.py",
        "adapters/kuzu/runners/run_main.py",
        "adapters/kuzu/runners/run_shortest.py",
        "adapters/kuzu/runners/run_update.py",
        "adapters/kuzu/runners/update_query_loader.py",
        "adapters/kuzu/queries/Update/manifest.json",
        "adapters/orientdb/loaders/load_orientdb_data.py",
        "adapters/orientdb/runners/run_orientdb.py",
        "adapters/postgresql/loaders/load.py",
        "adapters/postgresql/loaders/loader_core.py",
        "adapters/postgresql/loaders/prepare_age.py",
        "adapters/postgresql/runners/legacy/postgresql_benchmark_common.sh",
        "adapters/postgresql/runners/legacy/run_main_three_rounds.sh",
        "adapters/postgresql/runners/legacy/run_pure_join_three_rounds.sh",
        "adapters/postgresql/runners/legacy/run_update_three_rounds.sh",
        "adapters/postgresql/runners/legacy/run_update_single_round.sh",
    ]
    for rel in required:
        check((ROOT / rel).is_file(), f"workflow layout path missing: {rel}", errors)

    deprecated = [
        "benchmark/data-generation",
        "benchmark/schema",
        "benchmark/setup",
        "adapters/kuzu/load.py",
        "adapters/kuzu/run_main.py",
        "adapters/orientdb/load_orientdb_data.py",
        "adapters/orientdb/run_orientdb.py",
        "adapters/postgresql/runners/legacy/queries.sh",
        "adapters/postgresql/runners/legacy/queries1.sh",
        "adapters/postgresql/runners/legacy/queries2.sh",
        "adapters/postgresql/runners/legacy/queries4.sh",
        "adapters/postgresql/runners/legacy/queries5.sh",
        "adapters/postgresql/runners/legacy/queries6.sh",
    ]
    for rel in deprecated:
        check(not (ROOT / rel).exists(), f"deprecated workflow path remains: {rel}", errors)

    expected_adapter_entries = {"loaders", "queries", "runners"}
    for adapter in EXPECTED_COVERAGE:
        adapter_root = ROOT / "adapters" / adapter
        actual_entries = {path.name for path in adapter_root.iterdir()}
        check(
            actual_entries == expected_adapter_entries,
            f"adapter root layout differs for {adapter}: {sorted(actual_entries)}",
            errors,
        )


def validate_results(errors: list[str]) -> None:
    manifest = rows(RESULT_MANIFEST)
    source_manifest = rows(RESULT_MANIFEST.parent / "source_results.csv")
    source_by_path = {row["published_path"]: row for row in source_manifest}
    check({row["engine"] for row in manifest} == set(EXPECTED_COVERAGE), "results do not cover all seven engines", errors)
    check(
        {row["published_path"] for row in manifest} == set(source_by_path),
        "source and published result manifests cover different files",
        errors,
    )
    for row in manifest:
        path = ROOT / row["published_path"]
        source = source_by_path.get(row["published_path"], {})
        check(path.is_file(), f"published result missing: {row['published_path']}", errors)
        if path.is_file():
            check(path.stat().st_size == int(row["size_bytes"]), f"result size drift: {row['published_path']}", errors)
            check(sha256(path) == row["sha256"], f"result hash drift: {row['published_path']}", errors)
        check(row["source_size_bytes"] == source.get("size_bytes"), f"source result size provenance drift: {row['published_path']}", errors)
        check(row["source_sha256"] == source.get("sha256"), f"source result hash provenance drift: {row['published_path']}", errors)
        check(row["sanitization"] in {"none", "host_path_alias_normalization"}, f"unknown result sanitization: {row['published_path']}", errors)
        check(row["comparability"] != "comparable", "historical result incorrectly marked comparable", errors)


def validate_repository_hygiene(errors: list[str], strict_paths: bool) -> None:
    secret_patterns = [
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)\b(?:postgres(?:ql)?|mongodb(?:\+srv)?)://[^\s:@]+:[^\s@]+@"),
        re.compile(r"(?i)\b(?:create database|connect plocal:)[^\n]*\sadmin\s+admin\b"),
    ]
    private_ip = re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b")
    absolute_path = re.compile(
        r"(?<![A-Za-z0-9_.-])"
        r"(?:/home/[A-Za-z0-9_.-]+|/(?:data[23]?|workspace|root|mnt|ssd))(?:/|$)"
    )
    local_identity = re.compile(r"(?i)\b(?:h[x]{2}|t[e]ddy|m[m]db|bruce[l]ee)\b")
    for path in tracked_or_worktree_files():
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        check(path.stat().st_size <= 10 * 1024 * 1024, f"file exceeds 10 MiB publication limit: {rel}", errors)
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"AGENTS.md", "LICENSE", ".gitignore", ".gitattributes"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in secret_patterns:
            check(not pattern.search(text), f"possible secret in {rel}", errors)
        if rel != "docs/development/security.md":
            check(not private_ip.search(text), f"private IP in {rel}", errors)
        if strict_paths and not rel.startswith(ABSOLUTE_PATH_ALLOWLIST):
            check(not absolute_path.search(text), f"absolute host path in {rel}", errors)
            check(not local_identity.search(text), f"local identity in {rel}", errors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-paths", action="store_true", help="Reject absolute host paths outside documented legacy adapters.")
    args = parser.parse_args()
    errors: list[str] = []
    validate_queries(errors)
    validate_duckdb_query_mirror(errors)
    validate_known_semantics(errors)
    validate_coverage(errors)
    validate_data_and_updates(errors)
    validate_workflow_layout(errors)
    validate_results(errors)
    validate_repository_hygiene(errors, args.strict_paths)
    errors.extend(audit_query_semantics())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Validation failed with {len(errors)} error(s).")
        return 1
    print("GRBench repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
