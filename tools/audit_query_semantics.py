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
    "graindb": ".sql",
    "kuzu": ".cypher",
    "orientdb": ".sql",
    "postgresql": ".sql",
}
STATIC_SHORTEST_ADAPTERS = {"arangodb": ".js", "orientdb": ".sql"}
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
        if path.relative_to(CANONICAL).parts[0] not in {"Shortest_Path_Queries", "update"}:
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


def validate_updates(errors: list[str]) -> None:
    canonical_root = CANONICAL / "update" / "Update"
    graindb_root = ROOT / "adapters" / "graindb" / "queries" / "update" / "Update"
    for canonical_path in sorted(canonical_root.glob("*.sql")):
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
