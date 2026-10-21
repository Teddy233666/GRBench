#!/usr/bin/env python3
"""Generate relational-equivalent S-series queries for every system."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = ("agensgraph", "arangodb", "duckdb", "graindb", "orientdb", "postgresql")
THRESHOLDS = {"a": "8000", "b": "48000", "c": None}
PAPER_THRESHOLDS = {"a": "150", "b": "80", "c": "5"}


def condition(alias: str, variant: str) -> str:
    threshold = THRESHOLDS[variant]
    if threshold is not None:
        return f"{alias}.productivity > {threshold}"
    return f"{alias}.institutionid = 'I4210088668'"


def postgres_sql(query_id: str, variant: str, *, duck: bool) -> str:
    number = int(query_id[1])
    suffix = query_id[2]
    if number == 5:
        threshold = PAPER_THRESHOLDS[suffix]
        visited = "LIST_VALUE(CAST(p.paperid AS VARCHAR))" if duck else "ARRAY[p.paperid]::text[]"
        append = "list_append(w.visited, CAST(e.cited_paperid AS VARCHAR))" if duck else "w.visited || e.cited_paperid"
        contains = "NOT list_contains(w.visited, e.cited_paperid)" if duck else "NOT e.cited_paperid = ANY(w.visited)"
        return f"""-- Relational equivalent of {query_id}; recursive edge joins, no shortest-path syntax.
WITH RECURSIVE walk(paperid, depth, visited) AS (
    SELECT p.paperid, 0, {visited}
    FROM Papers p
    WHERE p.paperid = 'W4211259235'
    UNION ALL
    SELECT e.cited_paperid, w.depth + 1, {append}
    FROM walk w
    JOIN PaperReferences e ON e.citing_paperid = w.paperid
    WHERE w.depth < 1
      AND {contains}
)
SELECT MIN(p.paperid) AS ref_paperid
FROM walk w
JOIN Papers p ON p.paperid = w.paperid
WHERE p.citation_count < {threshold};
"""

    max_depth = {1: "NULL", 2: "3", 3: "4", 4: "NULL"}[number]
    min_depth = 0 if number == 4 else 1
    start = "I4210136388"
    visited = "LIST_VALUE(CAST(a.institutionid AS VARCHAR))" if duck else "ARRAY[a.institutionid]::text[]"
    append = "list_append(r.visited, CAST(e.associated_institution_id AS VARCHAR))" if duck else "r.visited || e.associated_institution_id"
    contains = "NOT list_contains(r.visited, e.associated_institution_id)" if duck else "NOT e.associated_institution_id = ANY(r.visited)"
    depth_filter = "" if max_depth == "NULL" else f"\n      AND r.depth < {max_depth}"
    endpoint_condition = condition("a", suffix)
    recursive = f"""WITH RECURSIVE reach(institutionid, depth, visited) AS (
    SELECT a.institutionid, 0, {visited}
    FROM Affiliations a
    WHERE a.institutionid = '{start}'
    UNION ALL
    SELECT e.associated_institution_id, r.depth + 1, {append}
    FROM reach r
    JOIN affl_assoc_affl e ON e.institution_id = r.institutionid
    WHERE {contains}{depth_filter}
)"""
    if number == 3:
        return f"""-- Relational equivalent of {query_id}; recursive edge joins plus a relational LEFT JOIN.
{recursive}, endpoints AS (
    SELECT DISTINCT a.institutionid
    FROM reach r
    JOIN Affiliations a ON a.institutionid = r.institutionid
    WHERE r.depth >= 1 AND {endpoint_condition}
)
SELECT MIN(cf.institution_id) AS institutionid
FROM endpoints e
LEFT JOIN contributed_from cf ON cf.institution_id = e.institutionid;
"""
    return f"""-- Relational equivalent of {query_id}; recursive edge joins, no shortest-path syntax.
{recursive}
SELECT MIN(a.institutionid) AS {('inst_for_institutionid' if suffix == 'a' else 'inst_eu_institutionid' if suffix == 'b' else 'inst_asia_institutionid')}
FROM reach r
JOIN Affiliations a ON a.institutionid = r.institutionid
WHERE r.depth >= {min_depth}
  AND {endpoint_condition};
"""


def orientdb_sql(query_id: str, variant: str) -> str:
    number = int(query_id[1])
    suffix = query_id[2]
    if number == 5:
        threshold = PAPER_THRESHOLDS[suffix]
        return f"""-- Relational equivalent of {query_id}; OrientDB SQL over edge/vertex classes.
SELECT MIN(paperid) AS ref_paperid
FROM Papers
WHERE (paperid = 'W4211259235' OR paperid IN (
    SELECT cited_paperid FROM PaperReferences
    WHERE citing_paperid = 'W4211259235'
))
AND citation_count < {threshold};
"""
    max_depth = {1: "", 2: "MAXDEPTH 3", 3: "MAXDEPTH 4", 4: ""}[number]
    minimum = 0 if number == 4 else 1
    endpoint = condition("v", suffix)
    traversal = (
        "TRAVERSE out('affl_assoc_affl') FROM "
        "(SELECT FROM Affiliations WHERE institutionid = 'I4210136388')"
    )
    if max_depth:
        traversal += f" {max_depth}"
    if number == 3:
        return f"""-- Relational equivalent of {query_id}; OrientDB uses TRAVERSE for the recursive closure.
SELECT MIN(cf.institution_id) AS institutionid
FROM contributed_from cf
WHERE cf.institution_id IN (
    SELECT institutionid FROM ({traversal})
    WHERE @class = 'Affiliations' AND {endpoint}
);
"""
    return f"""-- Relational equivalent of {query_id}; OrientDB uses TRAVERSE for the recursive closure.
SELECT MIN(institutionid) AS {('inst_for_institutionid' if suffix == 'a' else 'inst_eu_institutionid' if suffix == 'b' else 'inst_asia_institutionid')}
FROM ({traversal}) v
WHERE @class = 'Affiliations'
  AND $depth >= {minimum}
  AND {endpoint};
"""


def arango_js(query_id: str, variant: str) -> str:
    number = int(query_id[1])
    suffix = query_id[2]
    if number == 5:
        threshold = PAPER_THRESHOLDS[suffix]
        return f"""// Relational equivalent of {query_id}; edge-collection expansion over PaperReferences.
db._query(`
LET start = "Papers/W4211259235"
LET candidates = (
  FOR v, e, p IN 0..1 OUTBOUND start PaperReferences
    OPTIONS {{ order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }}
    FILTER v.citation_count < {threshold}
    RETURN v._key
)
RETURN MIN(candidates)
`)
"""
    min_depth = 0 if number == 4 else 1
    max_depth = {1: 1000000000, 2: 3, 3: 4, 4: 1000000000}[number]
    endpoint_filter = (
        f"v.productivity > {THRESHOLDS[suffix]}"
        if THRESHOLDS[suffix] is not None
        else "v._key == 'I4210088668'"
    )
    if number == 3:
        return f"""// Relational equivalent of {query_id}; collection-level expansion and join.
db._query(`
LET endpoints = (
  FOR v, e, p IN {min_depth}..{max_depth} OUTBOUND "Affiliations/I4210136388" affl_assoc_affl
    OPTIONS {{ order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }}
    FILTER {endpoint_filter}
    RETURN v._key
)
LET candidates = (
  FOR cf IN contributed_from
    FILTER PARSE_IDENTIFIER(cf._to).key IN endpoints
    RETURN PARSE_IDENTIFIER(cf._to).key
)
RETURN MIN(candidates)
`)
"""
    alias = "inst_for_institutionid" if suffix == "a" else "inst_eu_institutionid" if suffix == "b" else "inst_asia_institutionid"
    return f"""// Relational equivalent of {query_id}; edge-collection expansion, not AQL shortest-path syntax.
db._query(`
LET candidates = (
  FOR v, e, p IN {min_depth}..{max_depth} OUTBOUND "Affiliations/I4210136388" affl_assoc_affl
    OPTIONS {{ order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }}
    FILTER {endpoint_filter}
    RETURN v._key
)
RETURN MIN(candidates) AS {alias}
`)
"""


def main() -> None:
    for system in SYSTEMS:
        directory = ROOT / "benchmark" / system / "queries" / "Relational_Equivalent_Queries" / "Shortest_Path_Queries"
        directory.mkdir(parents=True, exist_ok=True)
        for number in range(1, 6):
            for suffix in "abc":
                query_id = f"S{number}{suffix}"
                if system == "arangodb":
                    text = arango_js(query_id, suffix)
                    extension = ".js"
                elif system == "orientdb":
                    text = orientdb_sql(query_id, suffix)
                    extension = ".sql"
                else:
                    text = postgres_sql(query_id, suffix, duck=system in {"duckdb", "graindb"})
                    extension = ".sql"
                (directory / f"{query_id}{extension}").write_text(text, encoding="utf-8")
    print("generated 90 shortest-path relational-equivalent files")


if __name__ == "__main__":
    main()
