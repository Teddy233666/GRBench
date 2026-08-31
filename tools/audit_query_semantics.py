#!/usr/bin/env python3
"""Check adapter query invariants that can be proven without a live DBMS.

This audit intentionally checks only stable semantic signatures. Passing it is
not a substitute for comparing complete result sets against an oracle.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "benchmark" / "queries" / "canonical"
STATIC_MAIN_ADAPTERS = {
    "agensgraph": ".sql",
    "arangodb": ".js",
    "duckdb": ".sql",
    "graindb": ".sql",
    "kuzu": ".cypher",
    "orientdb": ".sql",
    "postgresql": ".sql",
}
STATIC_SHORTEST_ADAPTERS = {
    "agensgraph": ".sql",
    "arangodb": ".js",
    "duckdb": ".sql",
    "kuzu": ".cypher",
    "orientdb": ".sql",
}
STATIC_PURE_JOIN_ADAPTERS = {
    "agensgraph": ".sql",
    "duckdb": ".sql",
    "graindb": ".sql",
    "orientdb": ".sql",
    "postgresql": ".sql",
}
ARANGODB_LEGACY_UNVERIFIED_PURE_JOIN = {
    f"High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Multi-Hop/2{suffix}.js"
    for suffix in "abc"
} | {
    f"High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Single-Hop/11{suffix}.js"
    for suffix in "abc"
} | {
    f"Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Hop/13{suffix}.js"
    for suffix in "abc"
} | {
    f"Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/{number}{suffix}.js"
    for number in (16, 17)
    for suffix in "abc"
} | {
    f"Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Single-Hop/23{suffix}.js"
    for suffix in "abc"
} | {
    f"Pure_Graph_Queries/{number}{suffix}.js"
    for number in (31, 32)
    for suffix in "abc"
}
ANCHOR_RE = re.compile(r"\b(?:W|A|F|I)\d{6,}\b")
PREDICATE_RE = {
    name: re.compile(
        rf"\b{name}\b[^\n;]{{0,60}}?(<=|>=|==|=|<|>)\s*['\"]?(-?\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    for name in ("citation_count", "h_index", "productivity", "year")
}
EDGE_NAMES = {
    "affl_assoc_affl",
    "affiliated_with",
    "Authors_Paper",
    "contributed_from",
    "Link_ClinicalTrials",
    "Link_NIH",
    "link_newsfeed",
    "Link_NSF",
    "link_patents",
    "link_twitter",
    "PaperFields",
    "PaperReferences",
    "papersources",
    "Papers_to_Authors",
}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalized_sql(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().rstrip(";").lower()


def anchors(value: str) -> set[str]:
    return set(ANCHOR_RE.findall(value))


def predicates(value: str) -> set[tuple[str, str, str]]:
    found = set()
    for property_name, pattern in PREDICATE_RE.items():
        for operator, number in pattern.findall(value):
            found.add((property_name, "=" if operator == "==" else operator, number))
    return found


def edge_dependencies(value: str) -> set[str]:
    lower = value.lower()
    found = set()
    for edge in EDGE_NAMES:
        if re.search(rf"(?<![a-z0-9_]){re.escape(edge.lower())}(?![a-z0-9_])", lower):
            # Both physical directions come from the same authorship relation.
            found.add("authorship" if edge.lower() in {"authors_paper", "papers_to_authors"} else edge.lower())
    return found


def main_queries() -> Iterable[Path]:
    for path in sorted(CANONICAL.rglob("*.sql")):
        if path.relative_to(CANONICAL).parts[0] not in {"Pure_Join_Queries", "Shortest_Path_Queries", "update"}:
            yield path


def compare_signature(
    canonical_path: Path,
    adapter_path: Path,
    adapter: str,
    errors: list[str],
    *,
    include_edges: bool,
) -> None:
    canonical_text = text(canonical_path)
    adapter_text = text(adapter_path)
    rel = canonical_path.relative_to(CANONICAL)
    for label, extractor in (("anchors", anchors), ("predicates", predicates)):
        expected = extractor(canonical_text)
        actual = extractor(adapter_text)
        if actual != expected:
            errors.append(f"{adapter} {rel}: {label} differ: expected={sorted(expected)}, actual={sorted(actual)}")
    if include_edges:
        expected_edges = edge_dependencies(canonical_text)
        actual_edges = edge_dependencies(adapter_text)
        if actual_edges != expected_edges:
            errors.append(
                f"{adapter} {rel}: edge dependencies differ: "
                f"expected={sorted(expected_edges)}, actual={sorted(actual_edges)}"
            )


def validate_main(errors: list[str]) -> None:
    for canonical_path in main_queries():
        rel = canonical_path.relative_to(CANONICAL)
        for adapter, suffix in STATIC_MAIN_ADAPTERS.items():
            adapter_path = ROOT / "adapters" / adapter / "queries" / rel.with_suffix(suffix)
            if not adapter_path.is_file():
                errors.append(f"missing {adapter} main query: {rel.with_suffix(suffix)}")
                continue
            compare_signature(canonical_path, adapter_path, adapter, errors, include_edges=True)


def validate_shortest_path(errors: list[str]) -> None:
    source_root = CANONICAL / "Shortest_Path_Queries"
    for canonical_path in sorted(source_root.glob("*.sql")):
        rel = canonical_path.relative_to(CANONICAL)
        for adapter, suffix in STATIC_SHORTEST_ADAPTERS.items():
            adapter_path = ROOT / "adapters" / adapter / "queries" / rel.with_suffix(suffix)
            if not adapter_path.is_file():
                errors.append(f"missing {adapter} shortest-path query: {rel.with_suffix(suffix)}")
                continue
            compare_signature(canonical_path, adapter_path, adapter, errors, include_edges=True)

    arango_root = ROOT / "adapters" / "arangodb" / "queries" / "Shortest_Path_Queries"
    required_fragments = {
        "1": ["OUTBOUND SHORTEST_PATH", "LENGTH(pathVertices) > 1", "RETURN end._key"],
        "2": ["OUTBOUND SHORTEST_PATH", "LENGTH(pathVertices) >= 2", "LENGTH(pathVertices) <= 4"],
        "3": ["OUTBOUND SHORTEST_PATH", "LENGTH(pathVertices) <= 5", "INBOUND end._id contributed_from"],
        "4": ["OUTBOUND SHORTEST_PATH", "LENGTH(pathVertices) >= 1", "RETURN end._key"],
        "5": ["UNION_DISTINCT", "1..1 OUTBOUND start PaperReferences", "RETURN MIN(candidates)"],
    }
    for path in sorted(arango_root.glob("*.js")):
        value = text(path)
        for fragment in required_fragments[path.stem[0]]:
            if fragment not in value:
                errors.append(f"ArangoDB shortest-path {path.name} lacks required fragment: {fragment}")


def validate_pure_join(errors: list[str]) -> None:
    source_root = CANONICAL / "Pure_Join_Queries"
    arango_root = ROOT / "adapters" / "arangodb" / "queries" / "Pure_Join_Queries"
    legacy_unverified = set()
    for canonical_path in sorted(source_root.rglob("*.sql")):
        rel = canonical_path.relative_to(source_root)
        for adapter, suffix in STATIC_PURE_JOIN_ADAPTERS.items():
            adapter_path = (
                ROOT
                / "adapters"
                / adapter
                / "queries"
                / "Pure_Join_Queries"
                / rel.with_suffix(suffix)
            )
            if not adapter_path.is_file():
                errors.append(f"missing {adapter} Pure Join query: {rel.with_suffix(suffix)}")
                continue
            compare_signature(canonical_path, adapter_path, adapter, errors, include_edges=True)

        arango_rel = rel.with_suffix(".js")
        arango_path = arango_root / arango_rel
        if arango_rel.as_posix() in ARANGODB_LEGACY_UNVERIFIED_PURE_JOIN:
            legacy_unverified.add(arango_rel.as_posix())
            if not arango_path.is_file():
                errors.append(f"missing requested legacy ArangoDB Pure Join query: {arango_rel}")
        elif arango_path.is_file():
            compare_signature(canonical_path, arango_path, "arangodb", errors, include_edges=True)
        else:
            errors.append(f"missing audited ArangoDB Pure Join query: {arango_rel}")

    if legacy_unverified != ARANGODB_LEGACY_UNVERIFIED_PURE_JOIN:
        errors.append(
            "ArangoDB legacy-unverified Pure Join inventory differs: "
            f"missing={sorted(ARANGODB_LEGACY_UNVERIFIED_PURE_JOIN - legacy_unverified)}, "
            f"unexpected={sorted(legacy_unverified - ARANGODB_LEGACY_UNVERIFIED_PURE_JOIN)}"
        )

    for suffix in "abc":
        orient17 = text(
            ROOT
            / "adapters/orientdb/queries/Pure_Join_Queries/Low_Join_Relational_Graph_Hybrid_Queries"
            / "Low-Join Multi-Subgraph Single"
            / f"17{suffix}.sql"
        )
        patent_branch = orient17.split("$q3 =", 1)[1]
        if "paperid = 'W2122344208'" not in patent_branch or "SELECT cited_paperid" in patent_branch:
            errors.append(f"OrientDB Pure Join 17{suffix} patent branch uses the wrong endpoint")


def validate_updates(errors: list[str]) -> None:
    canonical_root = CANONICAL / "update" / "Update"
    graindb_root = ROOT / "adapters" / "graindb" / "queries" / "Update"
    duckdb_root = ROOT / "adapters" / "duckdb" / "queries" / "Update"
    for canonical_path in sorted(canonical_root.glob("*.sql")):
        duckdb_path = duckdb_root / canonical_path.name
        if not duckdb_path.is_file():
            errors.append(f"missing DuckDB Update query: {canonical_path.name}")
        elif text(duckdb_path) != text(canonical_path):
            errors.append(f"DuckDB Update differs from canonical SQL: {canonical_path.name}")

        adapter_path = graindb_root / canonical_path.name
        if not adapter_path.is_file():
            errors.append(f"missing GrainDB Update query: {canonical_path.name}")
        elif normalized_sql(text(adapter_path)) != normalized_sql(text(canonical_path)):
            errors.append(f"GrainDB Update differs from canonical SQL: {canonical_path.name}")

    staging_names = set(
        re.findall(
            r"\bgrbench_update[0-9]+_[a-z0-9_]+\b",
            "\n".join(text(path).lower() for path in canonical_root.glob("*.sql")),
        )
    )
    manifest = text(ROOT / "benchmark" / "manifests" / "update_lifecycle.csv").lower()
    setup = text(ROOT / "scripts" / "data_generation" / "derive_update_staging.sql").lower()
    for staging_name in sorted(staging_names):
        if staging_name not in manifest and not staging_name.startswith("grbench_update3_"):
            errors.append(f"Update lifecycle does not declare staging dependency: {staging_name}")
        if not re.search(rf"create\s+table\s+{re.escape(staging_name)}\b", setup):
            errors.append(f"Update staging setup does not derive: {staging_name}")


def validate_high_risk_semantics(errors: list[str]) -> None:
    checks = {
        "adapters/agensgraph/queries/Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/16b.sql": [
            "g_ref.paperid)::text",
            "LEFT JOIN link_nobellaureates",
        ],
        "adapters/arangodb/queries/Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/18b.js": [
            "hasRows",
        ],
        "adapters/kuzu/queries/Pure_Graph_Queries/32a.cypher": ["OPTIONAL MATCH"],
        "adapters/kuzu/queries/Pure_Graph_Queries/32b.cypher": ["OPTIONAL MATCH"],
        "adapters/kuzu/queries/Pure_Graph_Queries/32c.cypher": ["OPTIONAL MATCH"],
    }
    for relative, fragments in checks.items():
        value = text(ROOT / relative)
        for fragment in fragments:
            if fragment not in value:
                errors.append(f"high-risk semantic fragment missing from {relative}: {fragment}")
    arango18 = text(
        ROOT
        / "adapters/arangodb/queries/Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/18b.js"
    )
    if "FOR nf IN" in arango18:
        errors.append("ArangoDB 18b optional Newsfeed branch regressed to an inner loop")


def audit() -> list[str]:
    errors: list[str] = []
    validate_main(errors)
    validate_pure_join(errors)
    validate_shortest_path(errors)
    validate_updates(errors)
    validate_high_risk_semantics(errors)
    return errors


def main() -> int:
    errors = audit()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Query semantic audit failed with {len(errors)} error(s).")
        return 1
    print("GRBench static query semantic audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
