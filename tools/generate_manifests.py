#!/usr/bin/env python3
"""Regenerate deterministic GRBench repository manifests."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "benchmark" / "queries" / "canonical"
MANIFESTS = ROOT / "benchmark" / "manifests"
RESULT_MANIFESTS = ROOT / "results" / "manifests"
SOURCE_RESULT_MANIFEST = RESULT_MANIFESTS / "source_results.csv"
ADAPTERS = [
    "agensgraph",
    "arangodb",
    "duckdb",
    "graindb",
    "kuzu",
    "orientdb",
    "postgresql",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def query_rows() -> list[dict[str, object]]:
    rows = []
    for path in sorted(CANONICAL.rglob("*.sql")):
        rel = path.relative_to(CANONICAL)
        if rel.parts[0] == "Shortest_Path_Queries":
            suite = "shortest_path"
            query_id = f"shortest_path/{path.stem}"
            category = rel.parts[0]
            subcategory = "sciscinet_any_shortest"
        elif rel.parts[0] == "update":
            suite = "update"
            query_id = f"update/{path.stem}"
            category = "update"
            subcategory = "Update"
        else:
            suite = "main"
            query_id = f"main/{path.stem}"
            category = rel.parts[0]
            subcategory = rel.parent.name
        rows.append(
            {
                "query_id": query_id,
                "suite": suite,
                "category": category,
                "subcategory": subcategory,
                "sql_file": path.name,
                "canonical_path": path.relative_to(ROOT).as_posix(),
                "sha256": digest(path),
            }
        )
    return rows


def adapter_location(adapter: str, query: dict[str, object]) -> tuple[str, str, str]:
    canonical_path = Path(str(query["canonical_path"]))
    rel = canonical_path.relative_to("benchmark/queries/canonical")
    suite = str(query["suite"])

    if adapter == "duckdb":
        return "canonical_sql", canonical_path.as_posix(), "DuckDB executes canonical SQL directly."
    if adapter == "kuzu" and suite in {"shortest_path", "update"}:
        runner = "run_shortest.py" if suite == "shortest_path" else "run_update.py"
        return "runtime_generated", f"adapters/kuzu/runners/{runner}", "Runner emits engine-specific Cypher."

    supported = {
        "agensgraph": {"main"},
        "arangodb": {"main", "shortest_path"},
        "graindb": {"main", "update"},
        "kuzu": {"main", "shortest_path", "update"},
        "orientdb": {"main", "shortest_path", "update"},
        "postgresql": {"main"},
    }
    if suite not in supported.get(adapter, set()):
        return "not_implemented", "", "No audited adapter query is currently published."

    suffix = {"arangodb": ".js", "kuzu": ".cypher"}.get(adapter, ".sql")
    adapter_rel = rel.with_suffix(suffix)
    path = ROOT / "adapters" / adapter / "queries" / adapter_rel
    if path.exists():
        return "static_adapter", path.relative_to(ROOT).as_posix(), "Audited engine-specific query file."
    return "missing", path.relative_to(ROOT).as_posix(), "Expected adapter file is absent."


def coverage_rows(queries: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for adapter in ADAPTERS:
        for query in queries:
            status, path, note = adapter_location(adapter, query)
            rows.append(
                {
                    "adapter": adapter,
                    "query_id": query["query_id"],
                    "suite": query["suite"],
                    "status": status,
                    "adapter_path": path,
                    "note": note,
                }
            )
    return rows


def data_rows() -> list[dict[str, object]]:
    import sys

    schema_dir = ROOT / "data" / "schema"
    sys.path.insert(0, str(schema_dir))
    from sciscinet import DATA_PROFILE, EDGES, PLAINS, VERTICES

    by_csv: dict[str, dict[str, list[str]]] = {}
    for kind, tables in (("vertex", VERTICES), ("edge", EDGES), ("plain", PLAINS)):
        for table in tables:
            entry = by_csv.setdefault(
                table.csv,
                {"logical_kinds": [], "logical_names": [], "keys_or_endpoints": []},
            )
            entry["logical_kinds"].append(kind)
            entry["logical_names"].append(table.name)
            if kind == "vertex":
                entry["keys_or_endpoints"].append(str(table.primary_key))
            elif kind == "edge":
                entry["keys_or_endpoints"].append(f"{table.from_vertex}->{table.to_vertex}")
    rows = []
    for source_csv, entry in sorted(by_csv.items()):
        rows.append(
            {
                "profile": DATA_PROFILE,
                "source_csv": source_csv,
                "logical_kinds": ";".join(entry["logical_kinds"]),
                "logical_names": ";".join(entry["logical_names"]),
                "keys_or_endpoints": ";".join(entry["keys_or_endpoints"]),
            }
        )
    return rows


def pure_join_rows(queries: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for query in queries:
        if query["suite"] != "main":
            continue
        rel = Path(str(query["canonical_path"])).relative_to("benchmark/queries/canonical")
        rows.append(
            {
                "alias_id": f"pure_join/{Path(str(query['sql_file'])).stem}",
                "canonical_query_id": query["query_id"],
                "historical_path": f"tasks/sciscinet_tasks/Pure_Join_Queries/{rel.as_posix()}",
                "status": "logical_alias_not_executed",
                "note": "Relational implementation of the same logical query; excluded from duplicate workload execution.",
            }
        )
    return rows


def update_rows() -> list[dict[str, object]]:
    targets = {
        "1": "Papers",
        "2": "PaperReferences",
        "3": "Papers;PaperReferences;Papers_to_Authors;Authors_Paper;contributed_from;PaperFields;Link_NSF;Link_NIH;Link_ClinicalTrials;link_newsfeed;link_twitter",
        "4": "Authors_Gender",
        "5": "Papers_to_Authors",
        "6": "Authors_Gender;Papers_to_Authors;affiliated_with",
    }
    staging = {
        "1": "grbench_update1_papers",
        "2": "grbench_update2_edges",
        "3": (
            "grbench_update1_papers;grbench_update3_paperreferences;"
            "grbench_update1_papers_to_authors;grbench_update3_authors_paper;"
            "grbench_update3_contributed_from;grbench_update3_paperfields;"
            "grbench_update3_link_nsf;grbench_update3_link_nih;"
            "grbench_update3_link_clinicaltrials;grbench_update3_link_newsfeed;"
            "grbench_update3_link_twitter"
        ),
        "4": "grbench_update4_authors_gender",
        "5": "grbench_update5_papers_to_authors",
        "6": "grbench_update4_authors_gender;grbench_update6_papers_to_authors;grbench_update6_affiliated_with",
    }
    rows = []
    for number in range(1, 7):
        delete = f"{number}a.sql"
        restore = f"{number}b.sql"
        rows.extend(
            [
                {
                    "sql_file": delete,
                    "operation": "delete",
                    "unmeasured_setup": "",
                    "unmeasured_compensation": restore,
                    "target_tables": targets[str(number)],
                    "staging_inputs": staging[str(number)],
                    "timing_boundary": "statement execution and result consumption only",
                },
                {
                    "sql_file": restore,
                    "operation": "restore",
                    "unmeasured_setup": delete,
                    "unmeasured_compensation": "",
                    "target_tables": targets[str(number)],
                    "staging_inputs": staging[str(number)],
                    "timing_boundary": "statement execution and result consumption only",
                },
            ]
        )
    return rows


def result_rows() -> list[dict[str, object]]:
    provenance = {
        "agensgraph": ("legacy_core/test/agensgrph", "legacy_observed", "Legacy runner output; query revision and repeat contract predate canonical_full_v1."),
        "arangodb": ("legacy_core/test/arangodb", "legacy_observed", "Legacy runner output; not rerun after adapter semantic corrections."),
        "duckdb": ("legacy_core/test/duckdb", "legacy_observed", "Historical files include duplicate Pure Join rows in the main CSV."),
        "graindb": ("legacy_core/test/graindb", "legacy_observed", "Legacy runner output; header format is not normalized."),
        "kuzu": ("kuzu_poc/results", "latest_observed", "Three-run median file with targeted 1000 Hz replacements; predates final canonical audit."),
        "orientdb": ("orientdb_benchmark/results", "legacy_observed", "Single-run partial formal artifact; current Contract-v4 run is intentionally not copied while active."),
        "postgresql": ("legacy_core/test/postgresql", "legacy_observed", "Legacy runner output; sf10_4 and formal repeat provenance are incomplete."),
    }
    with SOURCE_RESULT_MANIFEST.open(newline="", encoding="utf-8") as handle:
        source_rows = {
            row["published_path"]: row for row in csv.DictReader(handle)
        }

    rows = []
    base = ROOT / "results"
    for engine in ADAPTERS:
        for path in sorted((base / engine).rglob("*")):
            if not path.is_file():
                continue
            source_root, grade, note = provenance[engine]
            published_path = path.relative_to(ROOT).as_posix()
            source = source_rows[published_path]
            published_sha256 = digest(path)
            rows.append(
                {
                    "engine": engine,
                    "published_path": published_path,
                    "source_root_alias": source_root,
                    "source_filename": path.name,
                    "source_size_bytes": source["size_bytes"],
                    "source_sha256": source["sha256"],
                    "size_bytes": path.stat().st_size,
                    "sha256": published_sha256,
                    "sanitization": (
                        "none"
                        if published_sha256 == source["sha256"]
                        else "host_path_alias_normalization"
                    ),
                    "comparability": grade,
                    "note": note,
                }
            )
    return rows


def main() -> None:
    queries = query_rows()
    write_csv(
        MANIFESTS / "query_manifest.csv",
        ["query_id", "suite", "category", "subcategory", "sql_file", "canonical_path", "sha256"],
        queries,
    )
    write_csv(
        MANIFESTS / "adapter_coverage.csv",
        ["adapter", "query_id", "suite", "status", "adapter_path", "note"],
        coverage_rows(queries),
    )
    write_csv(
        MANIFESTS / "data_profile.csv",
        ["profile", "source_csv", "logical_kinds", "logical_names", "keys_or_endpoints"],
        data_rows(),
    )
    write_csv(
        MANIFESTS / "pure_join_aliases.csv",
        ["alias_id", "canonical_query_id", "historical_path", "status", "note"],
        pure_join_rows(queries),
    )
    write_csv(
        MANIFESTS / "update_lifecycle.csv",
        ["sql_file", "operation", "unmeasured_setup", "unmeasured_compensation", "target_tables", "staging_inputs", "timing_boundary"],
        update_rows(),
    )
    write_csv(
        RESULT_MANIFESTS / "published_results.csv",
        [
            "engine", "published_path", "source_root_alias", "source_filename",
            "source_size_bytes", "source_sha256", "size_bytes", "sha256",
            "sanitization", "comparability", "note",
        ],
        result_rows(),
    )


if __name__ == "__main__":
    main()
