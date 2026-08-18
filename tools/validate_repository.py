#!/usr/bin/env python3
"""Validate GRBench's public repository contract without opening a database."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
EXPECTED_SUITES = {"main": 96, "shortest_path": 15, "update": 12}
EXPECTED_COVERAGE = {
    "agensgraph": Counter({"static_adapter": 96, "not_implemented": 27}),
    "arangodb": Counter({"static_adapter": 111, "not_implemented": 12}),
    "duckdb": Counter({"canonical_sql": 123}),
    "graindb": Counter({"static_adapter": 108, "not_implemented": 15}),
    "kuzu": Counter({"static_adapter": 96, "runtime_generated": 27}),
    "orientdb": Counter({"static_adapter": 123}),
    "postgresql": Counter({"static_adapter": 96, "not_implemented": 27}),
}
TEXT_SUFFIXES = {
    ".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".js", ".json", ".md",
    ".py", ".sh", ".sql", ".toml", ".csv", ".tsv", ".txt", ".yaml", ".yml",
}
ABSOLUTE_PATH_ALLOWLIST = (
    "tools/sanitize_result_paths.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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
    check(len({row["query_id"] for row in manifest}) == 123, "query IDs are not unique", errors)
    for row in manifest:
        path = ROOT / row["canonical_path"]
        check(path.is_file(), f"missing canonical query: {path.relative_to(ROOT)}", errors)
        if path.is_file():
            check(sha256(path) == row["sha256"], f"stale query hash: {path.relative_to(ROOT)}", errors)

    update_names = sorted(path.name for path in (CANONICAL / "update" / "Update").glob("*.sql"))
    check(update_names == [f"{n}{s}.sql" for n in range(1, 7) for s in "ab"], "canonical Update IDs must be 1a..6b", errors)
    check(not list((CANONICAL / "update").rglob("*c.sql")), "legacy c Update leaked into canonical", errors)


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

    agens16 = next((ROOT / "adapters/agensgraph/queries").rglob("16b.sql")).read_text()
    check("g_ref.paperid)::text" in agens16 and "g_ref.ref_paperid)::text" not in agens16.split("LEFT JOIN link_nobellaureates", 1)[1], "AgensGraph 16b Nobel endpoint regressed", errors)
    arango18 = next((ROOT / "adapters/arangodb/queries").rglob("18b.js")).read_text()
    check("hasRows" in arango18 and "FOR nf IN" not in arango18, "ArangoDB 18b optional join regressed", errors)


def validate_coverage(errors: list[str]) -> None:
    coverage = rows(MANIFESTS / "adapter_coverage.csv")
    check(len(coverage) == 7 * 123, "adapter coverage must contain 861 rows", errors)
    by_adapter: dict[str, Counter[str]] = {}
    for row in coverage:
        by_adapter.setdefault(row["adapter"], Counter())[row["status"]] += 1
        if row["status"] in {"static_adapter", "runtime_generated", "canonical_sql"}:
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
    validate_known_semantics(errors)
    validate_coverage(errors)
    validate_data_and_updates(errors)
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
