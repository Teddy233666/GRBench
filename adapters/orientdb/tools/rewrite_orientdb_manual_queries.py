#!/usr/bin/env python3
"""Generate manual OrientDB-compatible rewrites for GRBench sciscinet SQL.

The source query directory is left untouched.  The generated statements avoid
SQL/PGQ GRAPH_TABLE and ANSI JOIN syntax, using OrientDB scalar LET subqueries,
nested IN predicates, MATCH-compatible shortestPath calls, and update scripts
for edge inserts.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


TOOL_DIR = Path(__file__).resolve().parent
ADAPTER_DIR = TOOL_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
ROOT = ADAPTER_DIR
SOURCE_ROOT = REPO_ROOT / "benchmark" / "queries" / "canonical"
OUTPUT_ROOT = REPO_ROOT / ".local" / "orientdb" / "generated" / "manual-queries"
PURE_JOIN_ROOT = SOURCE_ROOT / "Pure_Join_Queries"


@dataclass
class Projection:
    alias: str
    column: str
    output: str
    raw: str


@dataclass
class JoinEdge:
    left_alias: str
    left_column: str
    right_alias: str
    right_column: str
    join_type: str

    def other(self, alias: str) -> Optional[str]:
        if alias == self.left_alias:
            return self.right_alias
        if alias == self.right_alias:
            return self.left_alias
        return None

    def columns_for(self, alias: str) -> Tuple[str, str]:
        if alias == self.left_alias:
            return self.left_column, self.right_column
        if alias == self.right_alias:
            return self.right_column, self.left_column
        raise ValueError(alias)


@dataclass
class JoinQuery:
    projections: List[Projection]
    alias_to_class: Dict[str, str]
    filters: Dict[str, List[str]]
    edges: List[JoinEdge]
    base_alias: str
    original: str = ""


@dataclass
class RewriteResult:
    status: str
    method: str
    sql: str
    source_basis: str
    notes: str = ""


def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n\r]*", " ", sql)
    return sql


def normalize_sql(sql: str) -> str:
    sql = strip_comments(sql).replace("\r", "\n")
    sql = re.sub(r"\s+", " ", sql).strip()
    sql = re.sub(r",\s+FROM\b", " FROM", sql, flags=re.I)
    return sql.rstrip(";")


def split_top_level_commas(text: str) -> List[str]:
    out: List[str] = []
    buf: List[str] = []
    depth = 0
    in_single = False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "'":
            buf.append(ch)
            if in_single and i + 1 < len(text) and text[i + 1] == "'":
                buf.append(text[i + 1])
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue
        if not in_single:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                piece = "".join(buf).strip()
                if piece:
                    out.append(piece)
                buf = []
                i += 1
                continue
        buf.append(ch)
        i += 1
    piece = "".join(buf).strip()
    if piece:
        out.append(piece)
    return out


def split_conditions(text: str) -> List[str]:
    pieces = re.split(r"\s+AND\s+", text.strip(), flags=re.I)
    return [p.strip(" ()") for p in pieces if p.strip(" ()")]


def parse_projection(piece: str, index: int) -> Projection:
    m = re.match(
        r"MIN\s*\(\s*([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\s*\)\s*(?:AS\s+([A-Za-z_][\w]*))?$",
        piece,
        flags=re.I,
    )
    if not m:
        raise ValueError(f"unsupported projection: {piece}")
    alias, column, out = m.groups()
    return Projection(alias=alias, column=column, output=out or f"min_{index}", raw=piece)


def parse_join_sql(sql: str) -> JoinQuery:
    norm = normalize_sql(sql)
    m = re.match(r"SELECT\s+(.*?)\s+FROM\s+(.*?)(?:\s+WHERE\s+(.*))?$", norm, flags=re.I | re.S)
    if not m:
        raise ValueError("not a SELECT/FROM query")
    select_part, from_part, where_part = m.groups()
    projections = [parse_projection(p, i) for i, p in enumerate(split_top_level_commas(select_part))]

    join_re = re.compile(r"\b(LEFT\s+JOIN|INNER\s+JOIN|JOIN)\s+([A-Za-z_][\w]*)\s+([A-Za-z_][\w]*)\s+ON\s+", flags=re.I)
    matches = list(join_re.finditer(from_part))
    base_text = from_part[: matches[0].start() if matches else len(from_part)].strip()
    bm = re.match(r"([A-Za-z_][\w]*)\s+([A-Za-z_][\w]*)$", base_text)
    if not bm:
        raise ValueError(f"unsupported base FROM: {base_text}")

    alias_to_class: Dict[str, str] = {bm.group(2): bm.group(1)}
    base_alias = bm.group(2)
    filters: Dict[str, List[str]] = defaultdict(list)
    edges: List[JoinEdge] = []

    for i, jm in enumerate(matches):
        join_type = "LEFT" if jm.group(1).upper().startswith("LEFT") else "INNER"
        table = jm.group(2)
        alias = jm.group(3)
        alias_to_class[alias] = table
        cond_start = jm.end()
        cond_end = matches[i + 1].start() if i + 1 < len(matches) else len(from_part)
        for cond in split_conditions(from_part[cond_start:cond_end]):
            add_condition(cond, filters, edges, join_type)

    if where_part:
        for cond in split_conditions(where_part):
            add_condition(cond, filters, edges, "INNER")

    return JoinQuery(
        projections=projections,
        alias_to_class=alias_to_class,
        filters=dict(filters),
        edges=edges,
        base_alias=base_alias,
        original=norm,
    )


def add_condition(
    cond: str,
    filters: Dict[str, List[str]],
    edges: List[JoinEdge],
    join_type: str,
) -> None:
    cond = cond.strip()
    eq = re.match(r"([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\s*=\s*([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)$", cond)
    if eq:
        edges.append(
            JoinEdge(
                left_alias=eq.group(1),
                left_column=eq.group(2),
                right_alias=eq.group(3),
                right_column=eq.group(4),
                join_type=join_type,
            )
        )
        return

    filt = re.match(
        r"([A-Za-z_][\w]*)\.([A-Za-z_][\w]*)\s*(LIKE|<=|>=|<>|!=|=|<|>)\s*(.+)$",
        cond,
        flags=re.I,
    )
    if filt:
        alias, column, op, value = filt.groups()
        filters[alias].append(f"{column} {op.upper()} {value.strip()}")
        return

    raise ValueError(f"unsupported condition: {cond}")


def inner_component(query: JoinQuery) -> Set[str]:
    seen = {query.base_alias}
    changed = True
    while changed:
        changed = False
        for edge in query.edges:
            if edge.join_type != "INNER":
                continue
            if edge.left_alias in seen and edge.right_alias not in seen:
                seen.add(edge.right_alias)
                changed = True
            if edge.right_alias in seen and edge.left_alias not in seen:
                seen.add(edge.left_alias)
                changed = True
    return seen


def shortest_path_aliases(query: JoinQuery, start: str, goals: Set[str]) -> Set[str]:
    if start in goals:
        return {start}
    graph: Dict[str, List[str]] = defaultdict(list)
    for edge in query.edges:
        graph[edge.left_alias].append(edge.right_alias)
        graph[edge.right_alias].append(edge.left_alias)
    prev: Dict[str, Optional[str]] = {start: None}
    q: deque[str] = deque([start])
    goal: Optional[str] = None
    while q and goal is None:
        cur = q.popleft()
        for nxt in graph[cur]:
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt in goals:
                goal = nxt
                break
            q.append(nxt)
    if goal is None:
        return {start}
    path: Set[str] = set()
    cur: Optional[str] = goal
    while cur is not None:
        path.add(cur)
        cur = prev[cur]
    return path


def required_aliases(query: JoinQuery, target: str) -> Set[str]:
    inner = inner_component(query)
    return set(inner) | shortest_path_aliases(query, target, inner)


def condition_for_alias(
    query: JoinQuery,
    alias: str,
    required: Set[str],
    parent: Optional[str] = None,
    seen_edges: Optional[Set[int]] = None,
) -> str:
    seen_edges = seen_edges or set()
    parts = list(query.filters.get(alias, []))
    for idx, edge in enumerate(query.edges):
        if idx in seen_edges:
            continue
        other = edge.other(alias)
        if other is None or other == parent or other not in required:
            continue
        own_col, other_col = edge.columns_for(alias)
        sub_where = condition_for_alias(query, other, required, alias, seen_edges | {idx})
        where = f" WHERE {sub_where}" if sub_where else ""
        parts.append(
            f"{own_col} IN (SELECT {other_col} FROM {query.alias_to_class[other]}{where})"
        )
    return " AND ".join(parts)


def orientdb_from_join_sql(sql: str, method: str, source_basis: str) -> RewriteResult:
    query = parse_join_sql(sql)
    lets: List[str] = []
    select_items: List[str] = []
    for i, projection in enumerate(query.projections):
        required = required_aliases(query, projection.alias)
        where = condition_for_alias(query, projection.alias, required)
        where_clause = f" WHERE {where}" if where else ""
        lets.append(
            f"    $q{i} = (SELECT MIN({projection.column}) AS v FROM "
            f"{query.alias_to_class[projection.alias]}{where_clause})"
        )
        select_items.append(f"    $q{i}[0].v AS {projection.output}")

    sql_out = "SELECT\n" + ",\n".join(select_items) + "\nLET\n" + ",\n".join(lets) + ";\n"
    return RewriteResult("REWRITTEN", method, sql_out, source_basis)


def pure_join_basis(rel_path: str) -> Optional[Path]:
    category = rel_path.split("/", 1)[0]
    if category == "Pure_Join_Queries":
        return SOURCE_ROOT / rel_path
    if category in {"High_Join_Relational_Graph_Hybrid_Queries", "Low_Join_Relational_Graph_Hybrid_Queries"}:
        candidate = PURE_JOIN_ROOT / rel_path
        if candidate.exists():
            return candidate
    return None


def graph_join_sql(number: int, variant: str) -> str:
    threshold_map = {
        25: {"a": "", "b": " AND inst3.h_index >= 1000", "c": " AND inst3.h_index >= 1500"},
        26: {"a": "<= 3", "b": "<= 1", "c": "= 1"},
        27: {"a": "<= 3", "b": "<= 1", "c": "= 1"},
        28: {"a": "<= 3", "b": "<= 1", "c": "= 1"},
        29: {"a": "", "b": " AND m2.h_index >= 1000", "c": " AND m2.h_index >= 1500"},
        30: {"a": "<= 3", "b": "<= 1", "c": "= 1"},
        31: {"a": "< 150", "b": "< 80", "c": "< 5"},
    }
    if number == 25:
        extra = threshold_map[number][variant]
        return (
            "SELECT MIN(inst0.institutionid) AS inst_0_institutionid "
            "FROM Affiliations inst0 "
            "JOIN affl_assoc_affl af1 ON inst0.institutionid = af1.institution_id "
            "JOIN Affiliations inst1 ON af1.associated_institution_id = inst1.institutionid "
            "JOIN affl_assoc_affl af2 ON inst1.institutionid = af2.institution_id "
            "JOIN Affiliations inst2 ON af2.associated_institution_id = inst2.institutionid "
            "JOIN affl_assoc_affl af3 ON inst2.institutionid = af3.institution_id "
            "JOIN Affiliations inst3 ON af3.associated_institution_id = inst3.institutionid "
            f"WHERE inst0.institutionid LIKE 'I42101230%'{extra};"
        )
    if number == 26:
        op = threshold_map[number][variant]
        return (
            "SELECT MIN(p.paperid) AS cited_paperid "
            "FROM Papers p "
            "JOIN Link_NIH l ON p.paperid = l.paperid "
            "JOIN NIH_Metadata n ON l.award_id = n.award_id "
            f"WHERE p.paperid LIKE 'W423590139%' AND p.citation_count {op};"
        )
    if number == 27:
        op = threshold_map[number][variant]
        return (
            "SELECT MIN(p.paperid) AS paperid, MIN(nsf.award_id) AS award_id "
            "FROM Papers p "
            "JOIN Link_NIH lnih ON p.paperid = lnih.paperid "
            "JOIN NIH_Metadata nih ON lnih.award_id = nih.award_id "
            "LEFT JOIN Link_NSF lnsf ON p.paperid = lnsf.paperid "
            "LEFT JOIN NSF_Metadata nsf ON lnsf.award_id = nsf.award_id "
            f"WHERE p.paperid LIKE 'W423590139%' AND p.citation_count {op};"
        )
    if number == 28:
        op = threshold_map[number][variant]
        return (
            "SELECT MIN(ref.paperid) AS ref_paper_id, MIN(nsf.award_id) AS award_id "
            "FROM Papers p4 "
            "JOIN PaperReferences r1 ON p4.paperid = r1.citing_paperid "
            "JOIN Papers ref ON r1.cited_paperid = ref.paperid "
            "LEFT JOIN Link_NSF lnsf ON p4.paperid = lnsf.paperid "
            "LEFT JOIN NSF_Metadata nsf ON lnsf.award_id = nsf.award_id "
            f"WHERE p4.paperid LIKE 'W423590139%' AND p4.citation_count {op};"
        )
    if number == 29:
        extra = threshold_map[number][variant]
        return (
            "SELECT MIN(assoc.institutionid) AS associated_institutionid "
            "FROM Affiliations inst "
            "JOIN affl_assoc_affl r1 ON inst.institutionid = r1.institution_id "
            "JOIN Affiliations m1 ON r1.associated_institution_id = m1.institutionid "
            "JOIN affl_assoc_affl r2 ON m1.institutionid = r2.institution_id "
            "JOIN Affiliations m2 ON r2.associated_institution_id = m2.institutionid "
            "JOIN affl_assoc_affl r3 ON m2.institutionid = r3.institution_id "
            "JOIN Affiliations m3 ON r3.associated_institution_id = m3.institutionid "
            "JOIN affl_assoc_affl r4 ON m3.institutionid = r4.institution_id "
            "JOIN Affiliations assoc ON r4.associated_institution_id = assoc.institutionid "
            f"WHERE inst.institutionid LIKE 'I42101230%'{extra};"
        )
    if number == 30:
        op = threshold_map[number][variant]
        return (
            "SELECT MIN(p.paperid) AS cited_paperid "
            "FROM Papers p "
            "JOIN Link_NSF l ON p.paperid = l.paperid "
            "JOIN NSF_Metadata n ON l.award_id = n.award_id "
            f"WHERE p.paperid LIKE 'W423590139%' AND p.citation_count {op};"
        )
    if number == 31:
        op = threshold_map[number][variant]
        return (
            "SELECT MIN(p4.paperid) AS p3, MIN(f.fieldid) AS fieldid "
            "FROM Papers p1 "
            "JOIN PaperReferences r1 ON p1.paperid = r1.citing_paperid "
            "JOIN Papers p5 ON r1.cited_paperid = p5.paperid "
            "JOIN PaperReferences r2 ON p5.paperid = r2.citing_paperid "
            "JOIN Papers p6 ON r2.cited_paperid = p6.paperid "
            "JOIN PaperReferences r3 ON p6.paperid = r3.citing_paperid "
            f"JOIN Papers p4 ON r3.cited_paperid = p4.paperid AND p4.citation_count {op} "
            "LEFT JOIN PaperFields pf ON p4.paperid = pf.paperid "
            "LEFT JOIN Fields f ON pf.fieldid = f.fieldid "
            "WHERE p1.paperid = 'W2122344208';"
        )
    if number == 32:
        extra = {"a": "", "b": " AND p6.citation_count < 100", "c": " AND p6.citation_count < 5"}[variant]
        return (
            "SELECT MIN(p3.paperid) AS p3, MIN(a.authorid) AS author, MIN(n.newsfeed_id) AS newsfeed "
            "FROM Papers p1 "
            "JOIN PaperReferences r1 ON p1.paperid = r1.citing_paperid "
            "JOIN Papers p5 ON r1.cited_paperid = p5.paperid "
            "JOIN PaperReferences r2 ON p5.paperid = r2.citing_paperid "
            "JOIN Papers p6 ON r2.cited_paperid = p6.paperid "
            "JOIN PaperReferences r3 ON p6.paperid = r3.citing_paperid "
            "JOIN Papers p3 ON r3.cited_paperid = p3.paperid "
            "LEFT JOIN Authors_Paper ap ON p1.paperid = ap.paperid "
            "LEFT JOIN Authors_Gender a ON ap.authorid = a.authorid "
            "LEFT JOIN link_newsfeed ln ON p1.paperid = ln.paperid "
            "LEFT JOIN Newsfeed_Metadata n ON ln.newsfeed_id = n.newsfeed_id "
            f"WHERE p1.paperid = 'W4235901390'{extra};"
        )
    raise ValueError(number)


def rewrite_pure_graph(rel_path: str, source_sql: str = "") -> Optional[RewriteResult]:
    m = re.match(r"Pure_Graph_Queries/(\d+)([abc])\.sql$", rel_path)
    if not m:
        return None
    number = int(m.group(1))
    variant = m.group(2)
    if 25 <= number <= 32:
        basis = graph_join_sql(number, variant)
        return orientdb_from_join_sql(basis, "manual_graph_table_to_nested_select", "original_graph_template")
    return None


def shortest_rewrite(rel_path: str, source_sql: str) -> Optional[RewriteResult]:
    m = re.match(r"Shortest_Path_Queries/(\d+)([abc])\.sql$", rel_path)
    if not m:
        return None
    number = int(m.group(1))
    variant = m.group(2)

    if number in {1, 2, 4}:
        dest_filter = {
            "a": "productivity > 8000",
            "b": "productivity > 48000",
            "c": "institutionid = 'I4210088668'",
        }[variant]
        bounds = {
            1: "AND shortestPath((SELECT FROM Affiliations WHERE institutionid = 'I4210136388'), @rid, 'OUT', 'affl_assoc_affl').size() > 1",
            2: "AND shortestPath((SELECT FROM Affiliations WHERE institutionid = 'I4210136388'), @rid, 'OUT', 'affl_assoc_affl').size() BETWEEN 2 AND 4",
            4: "AND shortestPath((SELECT FROM Affiliations WHERE institutionid = 'I4210136388'), @rid, 'OUT', 'affl_assoc_affl').size() > 0",
        }[number]
        sql = (
            "SELECT MIN(institutionid) AS institutionid\n"
            "FROM Affiliations\n"
            f"WHERE {dest_filter}\n"
            f"  {bounds};\n"
        )
        return RewriteResult("REWRITTEN", "manual_shortestPath_function", sql, "original_shortest_path")

    if number == 3:
        dest_filter = {
            "a": "productivity > 8000",
            "b": "productivity > 48000",
            "c": "institutionid = 'I4210088668'",
        }[variant]
        sql = (
            "SELECT MIN(institution_id) AS institutionid\n"
            "FROM contributed_from\n"
            "WHERE institution_id IN (\n"
            "    SELECT institutionid\n"
            "    FROM Affiliations\n"
            f"    WHERE {dest_filter}\n"
            "      AND shortestPath((SELECT FROM Affiliations WHERE institutionid = 'I4210136388'), @rid, 'OUT', 'affl_assoc_affl').size() BETWEEN 2 AND 5\n"
            ");\n"
        )
        return RewriteResult("REWRITTEN", "manual_shortestPath_with_left_join_branch", sql, "original_shortest_path")

    if number == 5:
        threshold = {"a": "150", "b": "80", "c": "5"}[variant]
        sql = (
            "SELECT MIN(paperid) AS ref_paperid\n"
            "FROM Papers\n"
            "WHERE citation_count < " + threshold + "\n"
            "  AND (\n"
            "      paperid = 'W4211259235'\n"
            "      OR paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid = 'W4211259235')\n"
            "  );\n"
        )
        return RewriteResult("REWRITTEN", "manual_zero_or_one_hop_shortest_path", sql, "original_shortest_path")

    return None


def edge_insert_script(edge: str, rows: str, from_class: str, from_pk: str, from_col: str, to_class: str, to_pk: str, to_col: str, set_cols: Sequence[str]) -> str:
    assignments = ", ".join([f"{col} = $e.{col}" for col in set_cols])
    return (
        f"LET rows = (SELECT FROM {rows});\n"
        "FOREACH (e IN $rows) {\n"
        f"  LET created = CREATE EDGE {edge} "
        f"FROM (SELECT FROM {from_class} WHERE {from_pk} = $e.{from_col}) "
        f"TO (SELECT FROM {to_class} WHERE {to_pk} = $e.{to_col}) "
        f"SET {assignments};\n"
        "}\n"
    )


def script_sql(body: str) -> str:
    return "script sql\n" + body.rstrip() + "\nend\n"


def rewrite_update(rel_path: str, source_sql: str) -> Optional[RewriteResult]:
    if not rel_path.startswith("update/"):
        return None
    mapping: Dict[str, str] = {
        "update/Update/1a.sql": "DELETE FROM Papers\nWHERE year BETWEEN 2020 AND 2025 UNSAFE;\n",
        "update/Update/1b.sql": "INSERT INTO Papers\nSELECT *\nFROM grbench_update1_papers;\n",
        "update/Update/2a.sql": (
            "DELETE EDGE PaperReferences\n"
            "WHERE [citing_paperid, cited_paperid] IN (\n"
            "    SELECT [citing_paperid, cited_paperid]\n"
            "    FROM grbench_update2_edges\n"
            ");\n"
        ),
        "update/Update/2b.sql": script_sql(
            edge_insert_script("PaperReferences", "grbench_update2_edges", "Papers", "paperid", "citing_paperid", "Papers", "paperid", "cited_paperid", ["citing_paperid", "cited_paperid"])
        ),
        "update/Update/3a.sql": (
            "DELETE EDGE PaperReferences\nWHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers)\n"
            "   OR cited_paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE Papers_to_Authors\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE contributed_from\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE PaperFields\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE Link_NSF\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE Link_NIH\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE Link_ClinicalTrials\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE link_newsfeed\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE EDGE link_twitter\nWHERE paperid IN (SELECT paperid FROM grbench_update1_papers);\n\n"
            "DELETE FROM Papers\nWHERE year BETWEEN 2020 AND 2025 UNSAFE;\n"
        ),
        "update/Update/4a.sql": "DELETE FROM Authors_Gender\nWHERE h_index BETWEEN 10 AND 20 UNSAFE;\n",
        "update/Update/4b.sql": "INSERT INTO Authors_Gender\nSELECT *\nFROM grbench_update4_authors_gender;\n",
        "update/Update/5a.sql": (
            script_sql(
                "LET rows = (SELECT FROM grbench_update5_papers_to_authors);\n"
                "FOREACH (e IN $rows) {\n"
                "  DELETE EDGE Papers_to_Authors WHERE paperid = $e.paperid AND authorid = $e.authorid;\n"
                "}\n"
            )
        ),
        "update/Update/5b.sql": script_sql(
            edge_insert_script("Papers_to_Authors", "grbench_update5_papers_to_authors", "Papers", "paperid", "paperid", "Authors_Gender", "authorid", "authorid", ["paperid", "authorid"])
        ),
        "update/Update/6a.sql": (
            "DELETE EDGE Papers_to_Authors\nWHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);\n\n"
            "DELETE EDGE affiliated_with\nWHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);\n\n"
            "DELETE FROM Authors_Gender\nWHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender) UNSAFE;\n"
        ),
    }
    if rel_path == "update/Update/3b.sql":
        prefix = "INSERT INTO Papers\nSELECT *\nFROM grbench_update1_papers;\n\n"
        body = ""
        body += edge_insert_script("PaperReferences", "grbench_update3_paperreferences", "Papers", "paperid", "citing_paperid", "Papers", "paperid", "cited_paperid", ["citing_paperid", "cited_paperid"])
        body += edge_insert_script("Papers_to_Authors", "grbench_update3_papers_to_authors", "Papers", "paperid", "paperid", "Authors_Gender", "authorid", "authorid", ["paperid", "authorid"])
        body += edge_insert_script("Authors_Paper", "grbench_update3_authors_paper", "Authors_Gender", "authorid", "authorid", "Papers", "paperid", "paperid", ["paperid", "authorid"])
        body += edge_insert_script("contributed_from", "grbench_update3_contributed_from", "Papers", "paperid", "paperid", "Affiliations", "institutionid", "institution_id", ["paperid", "institution_id"])
        body += edge_insert_script("PaperFields", "grbench_update3_paperfields", "Papers", "paperid", "paperid", "Fields", "fieldid", "fieldid", ["paperid", "fieldid"])
        body += edge_insert_script("Link_NSF", "grbench_update3_link_nsf", "Papers", "paperid", "paperid", "NSF_Metadata", "award_id", "award_id", ["paperid", "award_id"])
        body += edge_insert_script("Link_NIH", "grbench_update3_link_nih", "Papers", "paperid", "paperid", "NIH_Metadata", "award_id", "award_id", ["paperid", "award_id"])
        body += edge_insert_script("Link_ClinicalTrials", "grbench_update3_link_clinicaltrials", "Papers", "paperid", "paperid", "clinicaltrials_metadata", "nct_id", "nct_id", ["paperid", "nct_id"])
        body += edge_insert_script("link_newsfeed", "grbench_update3_link_newsfeed", "Papers", "paperid", "paperid", "Newsfeed_Metadata", "newsfeed_id", "newsfeed_id", ["paperid", "newsfeed_id"])
        body += edge_insert_script("link_twitter", "grbench_update3_link_twitter", "Papers", "paperid", "paperid", "Twitter_Metadata", "tweet_id", "tweet_id", ["paperid", "tweet_id"])
        mapping[rel_path] = prefix + script_sql(body)
    if rel_path == "update/Update/6b.sql":
        prefix = "INSERT INTO Authors_Gender\nSELECT *\nFROM grbench_update4_authors_gender;\n\n"
        body = ""
        body += edge_insert_script("Papers_to_Authors", "grbench_update6_papers_to_authors", "Papers", "paperid", "paperid", "Authors_Gender", "authorid", "authorid", ["paperid", "authorid"])
        body += edge_insert_script("affiliated_with", "grbench_update6_affiliated_with", "Authors_Gender", "authorid", "authorid", "Affiliations", "institutionid", "institution_id", ["authorid", "institution_id"])
        mapping[rel_path] = prefix + script_sql(body)

    if rel_path not in mapping:
        raise ValueError(f"no update rewrite for {rel_path}")
    return RewriteResult("REWRITTEN", "manual_orientdb_update", mapping[rel_path], "original_update")


def rewrite_one(src: Path) -> RewriteResult:
    rel_path = str(src.relative_to(SOURCE_ROOT))
    source_sql = src.read_text(errors="replace")

    for fn in (rewrite_update, shortest_rewrite, rewrite_pure_graph):
        result = fn(rel_path, source_sql)
        if result is not None:
            return result

    basis = pure_join_basis(rel_path)
    if basis is not None and basis.exists():
        try:
            return orientdb_from_join_sql(
                basis.read_text(errors="replace"),
                "manual_join_to_nested_select",
                str(basis.relative_to(SOURCE_ROOT)),
            )
        except Exception as exc:
            raise RuntimeError(f"{rel_path}: failed to translate {basis}: {exc}") from exc

    raise RuntimeError(f"{rel_path}: no rewrite rule")


def source_sql_files() -> Iterable[Path]:
    return sorted(SOURCE_ROOT.rglob("*.sql"), key=lambda p: str(p.relative_to(SOURCE_ROOT)))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)

    manifest: List[Dict[str, str]] = []
    failures: List[str] = []
    for src in source_sql_files():
        rel_path = str(src.relative_to(SOURCE_ROOT))
        try:
            result = rewrite_one(src)
        except Exception as exc:
            failures.append(f"{rel_path}: {exc}")
            continue
        out = OUTPUT_ROOT / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.sql, encoding="utf-8")
        manifest.append(
            {
                "sql_file": rel_path,
                "status": result.status,
                "method": result.method,
                "source_basis": result.source_basis,
                "notes": result.notes,
            }
        )

    with (OUTPUT_ROOT / "rewrite_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["sql_file", "status", "method", "source_basis", "notes"])
        writer.writeheader()
        writer.writerows(manifest)

    (OUTPUT_ROOT / "rewrite_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "README.md").write_text(
        "# OrientDB manual sciscinet rewrites\n\n"
        f"Generated at: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Source root: `{SOURCE_ROOT}`\n\n"
        "The source SQL files were not modified.  These rewrites remove SQL/PGQ "
        "`GRAPH_TABLE`, ANSI `JOIN`, and edge `INSERT ... SELECT` constructs so "
        "the workload can be submitted to OrientDB 3.2 syntax.\n\n"
        "The benchmark runner is currently schema-only; `SCHEMA_ONLY_OK` means "
        "the statement parsed/executed against an empty schema, not that data "
        "correctness or performance has been validated.\n",
        encoding="utf-8",
    )

    print(f"generated={len(manifest)} output={OUTPUT_ROOT}")
    if failures:
        print("failures:")
        for failure in failures:
            print(f"  {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
