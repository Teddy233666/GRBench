#!/usr/bin/env python3
"""Generate OrientDB rewrites that prefer native graph traversal syntax.

This generator builds on rewrite_orientdb_manual_queries.py.  It keeps the
existing manual rewrites as a fallback, but emits OrientDB MATCH patterns for
Pure_Graph_Queries where the SQL/PGQ GRAPH_TABLE pattern maps directly to
loaded OrientDB edge classes.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import rewrite_orientdb_manual_queries as manual


TOOL_DIR = Path(__file__).resolve().parent
QUERIES_DIR = TOOL_DIR.parent
ADAPTER_DIR = QUERIES_DIR.parent
REPO_ROOT = ADAPTER_DIR.parents[1]
ROOT = ADAPTER_DIR
OUTPUT_ROOT = REPO_ROOT / ".local" / "orientdb" / "generated" / "native-graph-queries"


def graph_match_select(match: str, projection: str, output_alias: Optional[str] = None) -> str:
    return scalar_let_select([("q0", output_alias or projection, aggregate_match_sql(match, projection))])


def scalar_let_select(items: List[tuple[str, str, str]]) -> str:
    select_items = [f"    ${name}[0].v AS {alias}" for name, alias, _ in items]
    lets = [f"    ${name} = ({sql.rstrip(';')})" for name, _, sql in items]
    return "SELECT\n" + ",\n".join(select_items) + "\nLET\n" + ",\n".join(lets) + ";\n"


def aggregate_match_sql(match: str, projection: str) -> str:
    return (
        "SELECT MIN(" + projection + ") AS v\n"
        "FROM (\n"
        f"    {match}\n"
        ")"
    )


def native_pure_graph(rel_path: str) -> Optional[manual.RewriteResult]:
    name = Path(rel_path).name
    number = int(name[:-5])
    variant = name[-5]

    if number == 25:
        threshold = {"a": None, "b": 1000, "c": 1500}[variant]
        tail = "{class:Affiliations, as:inst3}"
        if threshold is not None:
            tail = f"{{class:Affiliations, as:inst3, where:(h_index >= {threshold})}}"
        match = (
            "MATCH {class:Affiliations, as:inst0, where:(institutionid LIKE 'I42101230%')}"
            ".out('affl_assoc_affl'){class:Affiliations, as:inst1}"
            ".out('affl_assoc_affl'){class:Affiliations, as:inst2}"
            f".out('affl_assoc_affl'){tail} "
            "RETURN inst0.institutionid AS inst_0_institutionid"
        )
        sql = graph_match_select(match, "inst_0_institutionid")
        return manual.RewriteResult("REWRITTEN", "native_match_fixed_path", sql, "original_graph_table")

    if number == 26:
        op = {"a": "<= 3", "b": "<= 1", "c": "= 1"}[variant]
        match = (
            "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}"
            ".out('Link_NIH'){class:NIH_Metadata, as:n} "
            "RETURN p.paperid AS paperid"
        )
        sql = graph_match_select(match, "paperid", "cited_paperid")
        return manual.RewriteResult("REWRITTEN", "native_match_single_edge", sql, "original_graph_table")

    if number == 27:
        op = {"a": "<= 3", "b": "<= 1", "c": "= 1"}[variant]
        base = (
            "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}"
            ".out('Link_NIH'){class:NIH_Metadata, as:nih} "
            "RETURN p.paperid AS paperid"
        )
        nsf = (
            "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}"
            ".out('Link_NIH'){class:NIH_Metadata, as:nih}, "
            "{as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf} "
            "RETURN nsf.award_id AS award_id"
        )
        sql = scalar_let_select(
            [
                ("q0", "paperid", aggregate_match_sql(base, "paperid")),
                ("q1", "award_id", aggregate_match_sql(nsf, "award_id")),
            ]
        )
        return manual.RewriteResult("REWRITTEN", "native_match_with_optional_branch_aggregate", sql, "original_graph_table_plus_left_join")

    if number == 28:
        op = {"a": "<= 3", "b": "<= 1", "c": "= 1"}[variant]
        refs = (
            "MATCH {class:Papers, as:p4, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}"
            ".out('PaperReferences'){class:Papers, as:ref} "
            "RETURN ref.paperid AS ref_paper_id"
        )
        nsf = (
            "MATCH {class:Papers, as:p4, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}"
            ".out('PaperReferences'){class:Papers, as:ref}, "
            "{as:p4}.out('Link_NSF'){class:NSF_Metadata, as:nsf} "
            "RETURN nsf.award_id AS award_id"
        )
        sql = scalar_let_select(
            [
                ("q0", "ref_paper_id", aggregate_match_sql(refs, "ref_paper_id")),
                ("q1", "award_id", aggregate_match_sql(nsf, "award_id")),
            ]
        )
        return manual.RewriteResult("REWRITTEN", "native_match_with_optional_branch_aggregate", sql, "original_graph_table_plus_left_join")

    if number == 29:
        threshold = {"a": None, "b": 1000, "c": 1500}[variant]
        m2 = "{class:Affiliations, as:m2}"
        if threshold is not None:
            m2 = f"{{class:Affiliations, as:m2, where:(h_index >= {threshold})}}"
        match = (
            "MATCH {class:Affiliations, as:inst, where:(institutionid LIKE 'I42101230%')}"
            ".out('affl_assoc_affl'){class:Affiliations, as:m1}"
            f".out('affl_assoc_affl'){m2}"
            ".out('affl_assoc_affl'){class:Affiliations, as:m3}"
            ".out('affl_assoc_affl'){class:Affiliations, as:assoc} "
            "RETURN assoc.institutionid AS associated_institutionid"
        )
        sql = graph_match_select(match, "associated_institutionid", "associated_institutionid")
        return manual.RewriteResult("REWRITTEN", "native_match_fixed_path", sql, "original_graph_table")

    if number == 30:
        op = {"a": "<= 3", "b": "<= 1", "c": "= 1"}[variant]
        match = (
            "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}"
            ".out('Link_NSF'){class:NSF_Metadata, as:n} "
            "RETURN p.paperid AS paperid"
        )
        sql = graph_match_select(match, "paperid", "cited_paperid")
        return manual.RewriteResult("REWRITTEN", "native_match_single_edge", sql, "original_graph_table")

    if number == 31:
        threshold = {"a": "< 150", "b": "< 80", "c": "< 5"}[variant]
        path = (
            "MATCH {class:Papers, as:p1, where:(paperid = 'W2122344208')}"
            ".out('PaperReferences'){class:Papers, as:p5}"
            ".out('PaperReferences'){class:Papers, as:p6}"
            f".out('PaperReferences'){{class:Papers, as:p3, where:(citation_count {threshold})}} "
            "RETURN p3.paperid AS p3"
        )
        field = (
            "MATCH {class:Papers, as:p1, where:(paperid = 'W2122344208')}"
            ".out('PaperReferences'){class:Papers, as:p5}"
            ".out('PaperReferences'){class:Papers, as:p6}"
            f".out('PaperReferences'){{class:Papers, as:p3, where:(citation_count {threshold})}}, "
            "{as:p3}.out('PaperFields'){class:Fields, as:f} "
            "RETURN f.fieldid AS fieldid"
        )
        sql = scalar_let_select(
            [
                ("q0", "p3", aggregate_match_sql(path, "p3")),
                ("q1", "fieldid", aggregate_match_sql(field, "fieldid")),
            ]
        )
        return manual.RewriteResult("REWRITTEN", "native_match_path_with_optional_branch_aggregate", sql, "original_graph_table_plus_left_join")

    if number == 32:
        extra = {"a": "", "b": " AND citation_count < 100", "c": " AND citation_count < 5"}[variant]
        path = (
            "MATCH {class:Papers, as:p1, where:(paperid = 'W4235901390')}"
            ".out('PaperReferences'){class:Papers, as:p5}"
            f".out('PaperReferences'){{class:Papers, as:p6, where:(true{extra})}}"
            ".out('PaperReferences'){class:Papers, as:p3} "
            "RETURN p3.paperid AS p3"
        )
        author = (
            "MATCH {class:Papers, as:p1, where:(paperid = 'W4235901390')}"
            ".out('PaperReferences'){class:Papers, as:p5}"
            f".out('PaperReferences'){{class:Papers, as:p6, where:(true{extra})}}"
            ".out('PaperReferences'){class:Papers, as:p3}, "
            "{as:p1}.in('Authors_Paper'){class:Authors_Gender, as:a} "
            "RETURN a.authorid AS author"
        )
        newsfeed = (
            "MATCH {class:Papers, as:p1, where:(paperid = 'W4235901390')}"
            ".out('PaperReferences'){class:Papers, as:p5}"
            f".out('PaperReferences'){{class:Papers, as:p6, where:(true{extra})}}"
            ".out('PaperReferences'){class:Papers, as:p3}, "
            "{as:p1}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n} "
            "RETURN n.newsfeed_id AS newsfeed"
        )
        sql = scalar_let_select(
            [
                ("q0", "p3", aggregate_match_sql(path, "p3")),
                ("q1", "author", aggregate_match_sql(author, "author")),
                ("q2", "newsfeed", aggregate_match_sql(newsfeed, "newsfeed")),
            ]
        )
        return manual.RewriteResult("REWRITTEN", "native_match_path_with_side_branches", sql, "original_graph_table")

    return None


def citation_path_match(citation_threshold: int, return_clause: str, extra_patterns: str = "") -> str:
    return paper_reference_path_match("W2122344208", 3, citation_threshold, return_clause, extra_patterns)


def paper_reference_path_match(
    start_paper: str,
    hops: int,
    citation_threshold: int,
    return_clause: str,
    extra_patterns: str = "",
) -> str:
    path = f"MATCH {{class:Papers, as:p, where:(paperid = '{start_paper}')}}"
    for hop in range(1, hops + 1):
        alias = "ref" if hop == hops else f"p{hop}"
        where = f", where:(citation_count < {citation_threshold})" if hop == hops else ""
        path += f".out('PaperReferences'){{class:Papers, as:{alias}{where}}}"
    return path + f"{extra_patterns} " + f"RETURN {return_clause}"


def match_projection_subquery(match: str, projection: str) -> str:
    return "SELECT " + projection + "\nFROM (\n    " + match + "\n)"


def plain_aggregate_sql(table: str, projection: str, where: str) -> str:
    return f"SELECT MIN({projection}) AS v\nFROM {table}\nWHERE {where}"


def source_aggregate_from_ref_path(citation_threshold: int) -> str:
    return source_aggregate_from_path("W2122344208", 3, citation_threshold, "ref")


def source_aggregate_from_path(start_paper: str, hops: int, citation_threshold: int, paper_alias: str) -> str:
    ref_subquery = match_projection_subquery(
        paper_reference_path_match(start_paper, hops, citation_threshold, f"{paper_alias}.paperid AS paperid"),
        "paperid",
    )
    return plain_aggregate_sql(
        "sources",
        "sourceid",
        "sourceid IN (\n"
        "    SELECT sourceid\n"
        "    FROM papersources\n"
        "    WHERE paperid IN (\n"
        f"        {ref_subquery}\n"
        "    )\n"
        ")",
    )


def plain_link_aggregate_from_orig_path(citation_threshold: int, table: str, projection: str) -> str:
    return plain_link_aggregate_from_path("W2122344208", 3, citation_threshold, "p", table, projection)


def plain_link_aggregate_from_path(
    start_paper: str,
    hops: int,
    citation_threshold: int,
    paper_alias: str,
    table: str,
    projection: str,
) -> str:
    paper_subquery = match_projection_subquery(
        paper_reference_path_match(start_paper, hops, citation_threshold, f"{paper_alias}.paperid AS paperid"),
        "paperid",
    )
    return plain_aggregate_sql(
        table,
        projection,
        "paperid IN (\n"
        f"    {paper_subquery}\n"
        ")",
    )


def linked_metadata_match(
    edge_class: str,
    target_class: str,
    citation_condition: str,
    return_clause: str,
) -> str:
    return (
        "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
        f"AND citation_count {citation_condition})}}"
        f".out('{edge_class}'){{class:{target_class}, as:n}} "
        f"RETURN {return_clause}"
    )


def linked_metadata_subquery(edge_class: str, target_class: str, citation_condition: str) -> str:
    return match_projection_subquery(
        linked_metadata_match(edge_class, target_class, citation_condition, "p.paperid AS paperid"),
        "paperid",
    )


def source_aggregate_from_linked_metadata(edge_class: str, target_class: str, citation_condition: str) -> str:
    paper_subquery = linked_metadata_subquery(edge_class, target_class, citation_condition)
    return plain_aggregate_sql(
        "sources",
        "sourceid",
        "sourceid IN (\n"
        "    SELECT sourceid\n"
        "    FROM papersources\n"
        "    WHERE paperid IN (\n"
        f"        {paper_subquery}\n"
        "    )\n"
        ")",
    )


def plain_aggregate_from_linked_metadata(
    edge_class: str,
    target_class: str,
    citation_condition: str,
    table: str,
    projection: str,
) -> str:
    paper_subquery = linked_metadata_subquery(edge_class, target_class, citation_condition)
    return plain_aggregate_sql(
        table,
        projection,
        "paperid IN (\n"
        f"    {paper_subquery}\n"
        ")",
    )


def native_hybrid_1_or_13(rel_path: str, high_join: bool) -> Optional[manual.RewriteResult]:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    author_threshold = {"a": 10, "b": 30, "c": 80}[variant]
    productivity_threshold = {"a": 1000, "b": 5000, "c": 10000}[variant]

    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    author_match = citation_path_match(
        citation_threshold,
        "a.authorid AS authorid",
        f", {{as:p}}.in('Authors_Paper'){{class:Authors_Gender, as:a, where:(h_index > {author_threshold})}}",
    )
    affiliation_projection = "ref.paperid AS paperid" if high_join else "inst.institutionid AS institutionid"
    affiliation_alias = "paperid" if high_join else "institutionid"
    affiliation_match = citation_path_match(
        citation_threshold,
        affiliation_projection,
        ", {as:ref}.out('contributed_from')"
        f"{{class:Affiliations, as:inst, where:(productivity > {productivity_threshold})}}",
    )
    author_subquery = match_projection_subquery(author_match, "authorid")

    items: List[tuple[str, str, str]] = [
        ("q0", "minPaper", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minAuthor", aggregate_match_sql(author_match, "authorid")),
        ("q2", "minAff", aggregate_match_sql(affiliation_match, affiliation_alias)),
    ]
    if high_join:
        items.append(("q3", "minSource", source_aggregate_from_ref_path(citation_threshold)))
        items.append(("q4", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_nobellaureates", "laureate_id")))
        items.append(
            (
                "q5",
                "minPatent",
                plain_aggregate_sql(
                    "author_details",
                    "authorid",
                    "authorid IN (\n"
                    f"    {author_subquery}\n"
                    ")",
                ),
            )
        )
    else:
        items.append(("q3", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_nobellaureates", "laureate_id")))
        items.append(
            (
                "q4",
                "minPatent",
                plain_aggregate_sql(
                    "author_details",
                    "authorid",
                    "authorid IN (\n"
                    f"    {author_subquery}\n"
                    ")",
                ),
            )
        )

    method = "native_match_hybrid_multi_subgraph_multi_hop" if high_join else "native_match_hybrid_low_join_multi_subgraph_hop"
    return manual.RewriteResult("REWRITTEN", method, scalar_let_select(items), "original_graph_table_hybrid")


def native_hybrid_2_or_14(rel_path: str, high_join: bool) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    author_threshold = {"a": 10, "b": 30, "c": 80}[variant]

    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    author_match = citation_path_match(
        citation_threshold,
        "a.authorid AS authorid",
        f", {{as:ref}}.in('Authors_Paper'){{class:Authors_Gender, as:a, where:(h_index > {author_threshold})}}",
    )
    nsf_match = citation_path_match(
        citation_threshold,
        "nsf.award_id AS award_id",
        ", {as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf}",
    )
    author_subquery = match_projection_subquery(author_match, "authorid")

    items: List[tuple[str, str, str]] = [
        ("q0", "minPaper", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minAuthor1", aggregate_match_sql(author_match, "authorid")),
        ("q2", "award_id", aggregate_match_sql(nsf_match, "award_id")),
    ]
    if high_join:
        items.append(("q3", "minSource", source_aggregate_from_ref_path(citation_threshold)))
        items.append(("q4", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_patents", "patent")))
        items.append(
            (
                "q5",
                "minAuthorid2",
                plain_aggregate_sql(
                    "author_details",
                    "authorid",
                    "authorid IN (\n"
                    f"    {author_subquery}\n"
                    ")",
                ),
            )
        )
    else:
        items.append(("q3", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_nobellaureates", "laureate_id")))
        items.append(
            (
                "q4",
                "minAuthorid2",
                plain_aggregate_sql(
                    "author_details",
                    "authorid",
                    "authorid IN (\n"
                    f"    {author_subquery}\n"
                    ")",
                ),
            )
        )

    method = "native_match_hybrid_multi_subgraph_multi_hop" if high_join else "native_match_hybrid_low_join_multi_subgraph_hop"
    return manual.RewriteResult("REWRITTEN", method, scalar_let_select(items), "original_graph_table_hybrid")


def native_hybrid_3(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]

    path_match = citation_path_match(citation_threshold, "ref.paperid AS paperid")
    field_match = citation_path_match(
        citation_threshold,
        "f.fieldid AS fieldid",
        ", {as:ref}.out('PaperFields'){class:Fields, as:f}",
    )
    newsfeed_match = citation_path_match(
        citation_threshold,
        "n.newsfeed_id AS newsfeed",
        ", {as:ref}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n}",
    )
    items: List[tuple[str, str, str]] = [
        ("q0", "p3", aggregate_match_sql(path_match, "paperid")),
        ("q1", "fieldid", aggregate_match_sql(field_match, "fieldid")),
        ("q2", "newsfeed", aggregate_match_sql(newsfeed_match, "newsfeed")),
        ("q3", "minSource", source_aggregate_from_path("W2122344208", 3, citation_threshold, "p")),
        ("q4", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_nobellaureates", "laureate_id")),
        ("q5", "minPatent", plain_link_aggregate_from_orig_path(citation_threshold, "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_multi_subgraph_multi_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_4_or_16(rel_path: str, high_join: bool) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    author_threshold = {"a": 10, "b": 30, "c": 80}[variant]
    start_paper = "W4211259235"

    path_match = paper_reference_path_match(start_paper, 1, citation_threshold, "p.paperid AS paperid")
    author_match = paper_reference_path_match(
        start_paper,
        1,
        citation_threshold,
        "a.authorid AS authorid",
        f", {{as:p}}.in('Authors_Paper'){{class:Authors_Gender, as:a, where:(h_index > {author_threshold})}}",
    )
    author_subquery = match_projection_subquery(author_match, "authorid")
    items: List[tuple[str, str, str]] = [
        ("q0", "minPaper", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minAuthor", aggregate_match_sql(author_match, "authorid")),
    ]
    if high_join:
        items.append(("q2", "minSource", source_aggregate_from_path(start_paper, 1, citation_threshold, "ref")))
        nobel_idx = "q3"
        patent_idx = "q4"
    else:
        nobel_idx = "q2"
        patent_idx = "q3"
    items.append((nobel_idx, "minNobel", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "p", "link_nobellaureates", "laureate_id")))
    items.append(
        (
            patent_idx,
            "minPatent",
            plain_aggregate_sql(
                "author_details",
                "authorid",
                "authorid IN (\n"
                f"    {author_subquery}\n"
                ")",
            ),
        )
    )
    method = "native_match_hybrid_multi_subgraph_single_hop" if high_join else "native_match_hybrid_low_join_multi_subgraph_single_hop"
    return manual.RewriteResult("REWRITTEN", method, scalar_let_select(items), "original_graph_table_hybrid")


def native_hybrid_5(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    start_paper = "W4211259235"

    path_match = paper_reference_path_match(start_paper, 1, citation_threshold, "p.paperid AS paperid")
    nsf_match = paper_reference_path_match(
        start_paper,
        1,
        citation_threshold,
        "nsf.award_id AS award_id",
        ", {as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf}",
    )
    items: List[tuple[str, str, str]] = [
        ("q0", "minPaper", aggregate_match_sql(path_match, "paperid")),
        ("q1", "award_id", aggregate_match_sql(nsf_match, "award_id")),
        ("q2", "minSource", source_aggregate_from_path(start_paper, 1, citation_threshold, "ref")),
        ("q3", "minNobel", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "p", "link_nobellaureates", "laureate_id")),
        ("q4", "minPatent", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "ref", "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_multi_subgraph_single_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_8_or_9(rel_path: str, normalized: bool) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    level0 = "normalized_citations_level0" if normalized else "hit_papers_level0"
    level1 = "normalized_citations_level1" if normalized else "hit_papers_level1"
    first_alias = "paperid" if normalized else "cited_paperid"

    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    items: List[tuple[str, str, str]] = [
        ("q0", first_alias, aggregate_match_sql(path_match, "paperid")),
        ("q1", "fieldid0", plain_link_aggregate_from_orig_path(citation_threshold, level0, "fieldid")),
        ("q2", "fieldid1", plain_link_aggregate_from_orig_path(citation_threshold, level1, "fieldid")),
        ("q3", "minNobel", plain_link_aggregate_from_path("W2122344208", 3, citation_threshold, "ref", "link_nobellaureates", "laureate_id")),
        ("q4", "minPatent", plain_link_aggregate_from_path("W2122344208", 3, citation_threshold, "ref", "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_single_subgraph_multi_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_7(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    items: List[tuple[str, str, str]] = [
        ("q0", "cited_paperid", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minSource", source_aggregate_from_ref_path(citation_threshold)),
        ("q2", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_nobellaureates", "laureate_id")),
        ("q3", "minPatent", plain_link_aggregate_from_orig_path(citation_threshold, "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_single_subgraph_multi_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_6(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    start_paper = "W4211259235"

    path_match = paper_reference_path_match(start_paper, 1, citation_threshold, "ref.paperid AS paperid")
    newsfeed_match = paper_reference_path_match(
        start_paper,
        1,
        citation_threshold,
        "n.newsfeed_id AS newsfeed",
        ", {as:p}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n}",
    )
    items: List[tuple[str, str, str]] = [
        ("q0", "p3", aggregate_match_sql(path_match, "paperid")),
        ("q1", "newsfeed", aggregate_match_sql(newsfeed_match, "newsfeed")),
        ("q2", "minSource", source_aggregate_from_path(start_paper, 1, citation_threshold, "p")),
        ("q3", "minNobel", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "p", "link_nobellaureates", "laureate_id")),
        ("q4", "minPatent", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "p", "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_multi_subgraph_single_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_15(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]

    path_match = citation_path_match(citation_threshold, "ref.paperid AS paperid")
    field_match = citation_path_match(
        citation_threshold,
        "f.fieldid AS fieldid",
        ", {as:ref}.out('PaperFields'){class:Fields, as:f}",
    )
    newsfeed_match = citation_path_match(
        citation_threshold,
        "n.newsfeed_id AS newsfeed",
        ", {as:p}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n}",
    )
    items: List[tuple[str, str, str]] = [
        ("q0", "p3", aggregate_match_sql(path_match, "paperid")),
        ("q1", "fieldid", aggregate_match_sql(field_match, "fieldid")),
        ("q2", "newsfeed", aggregate_match_sql(newsfeed_match, "newsfeed")),
        ("q3", "minNobel", plain_link_aggregate_from_orig_path(citation_threshold, "link_nobellaureates", "laureate_id")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_multi_subgraph_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_17(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    start_paper = "W4211259235"

    path_match = paper_reference_path_match(start_paper, 1, citation_threshold, "p.paperid AS paperid")
    nsf_match = paper_reference_path_match(
        start_paper,
        1,
        citation_threshold,
        "nsf.award_id AS award_id",
        ", {as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf}",
    )
    items: List[tuple[str, str, str]] = [
        ("q0", "minPaper", aggregate_match_sql(path_match, "paperid")),
        ("q1", "award_id", aggregate_match_sql(nsf_match, "award_id")),
        ("q2", "minNobel", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "p", "link_nobellaureates", "laureate_id")),
        ("q3", "minPatent", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "ref", "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_multi_subgraph_single_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_18(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    start_paper = "W2122344208"

    path_match = paper_reference_path_match(start_paper, 1, citation_threshold, "ref.paperid AS paperid")
    newsfeed_match = paper_reference_path_match(
        start_paper,
        1,
        citation_threshold,
        "n.newsfeed_id AS newsfeed",
        ", {as:p}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n}",
    )
    items: List[tuple[str, str, str]] = [
        ("q0", "p3", aggregate_match_sql(path_match, "paperid")),
        ("q1", "newsfeed", aggregate_match_sql(newsfeed_match, "newsfeed")),
        ("q2", "minNobel", plain_link_aggregate_from_path(start_paper, 1, citation_threshold, "p", "link_nobellaureates", "laureate_id")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_multi_subgraph_single_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_19(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    items: List[tuple[str, str, str]] = [
        ("q0", "cited_paperid", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minNobel", plain_link_aggregate_from_path("W2122344208", 3, citation_threshold, "ref", "link_nobellaureates", "laureate_id")),
        ("q2", "minPatent", plain_link_aggregate_from_orig_path(citation_threshold, "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_single_subgraph_multi_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_20(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    items: List[tuple[str, str, str]] = [
        ("q0", "cited_paperid", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minSource", source_aggregate_from_path("W2122344208", 3, citation_threshold, "p")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_single_subgraph_multi_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_21(rel_path: str) -> manual.RewriteResult:
    variant = Path(rel_path).stem[-1]
    citation_threshold = {"a": 150, "b": 80, "c": 5}[variant]
    path_match = citation_path_match(citation_threshold, "p.paperid AS paperid")
    items: List[tuple[str, str, str]] = [
        ("q0", "cited_paperid", aggregate_match_sql(path_match, "paperid")),
        ("q1", "fieldid", plain_link_aggregate_from_orig_path(citation_threshold, "hit_papers_level0", "fieldid")),
        ("q2", "minPatent", plain_link_aggregate_from_path("W2122344208", 3, citation_threshold, "ref", "link_patents", "patent")),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_single_subgraph_multi_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_10_11_12(rel_path: str) -> manual.RewriteResult:
    number = int(Path(rel_path).stem[:-1])
    variant = Path(rel_path).stem[-1]
    citation_condition = {"a": "<= 3", "b": "<= 1", "c": "= 1"}[variant]
    edge_class, target_class = {
        10: ("Link_NIH", "NIH_Metadata"),
        11: ("Link_NSF", "NSF_Metadata"),
        12: ("Link_ClinicalTrials", "clinicaltrials_metadata"),
    }[number]
    path_match = linked_metadata_match(edge_class, target_class, citation_condition, "p.paperid AS paperid")
    items: List[tuple[str, str, str]] = [
        ("q0", "cited_paperid", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minSource", source_aggregate_from_linked_metadata(edge_class, target_class, citation_condition)),
    ]
    if number == 10:
        items.append(("q2", "minNobel", plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "link_nobellaureates", "laureate_id")))
        items.append(("q3", "minPatent", plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "link_patents", "patent")))
    elif number == 11:
        items.append(("q2", "minNobel", plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "link_nobellaureates", "laureate_id")))
        items.append(("q3", "minh0paperid", plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "hit_papers_level0", "paperid")))
    else:
        items.append(("q2", "minh1paperid", plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "hit_papers_level1", "paperid")))
        items.append(("q3", "minPatent", plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "link_patents", "patent")))
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_single_subgraph_single_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid_22_23_24(rel_path: str) -> manual.RewriteResult:
    number = int(Path(rel_path).stem[:-1])
    variant = Path(rel_path).stem[-1]
    citation_condition = {"a": "<= 3", "b": "<= 1", "c": "= 1"}[variant]
    edge_class, target_class = {
        22: ("Link_NIH", "NIH_Metadata"),
        23: ("Link_NSF", "NSF_Metadata"),
        24: ("Link_ClinicalTrials", "clinicaltrials_metadata"),
    }[number]
    path_match = linked_metadata_match(edge_class, target_class, citation_condition, "p.paperid AS paperid")
    if number == 23:
        second = plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "link_patents", "patent")
    else:
        second = plain_aggregate_from_linked_metadata(edge_class, target_class, citation_condition, "link_nobellaureates", "laureate_id")
    items: List[tuple[str, str, str]] = [
        ("q0", "cited_paperid", aggregate_match_sql(path_match, "paperid")),
        ("q1", "minNobel", second),
    ]
    return manual.RewriteResult(
        "REWRITTEN",
        "native_match_hybrid_low_join_single_subgraph_single_hop",
        scalar_let_select(items),
        "original_graph_table_hybrid",
    )


def native_hybrid(rel_path: str) -> Optional[manual.RewriteResult]:
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Multi-Hop/1"):
        return native_hybrid_1_or_13(rel_path, high_join=True)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Multi-Hop/2"):
        return native_hybrid_2_or_14(rel_path, high_join=True)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Multi-Hop/3"):
        return native_hybrid_3(rel_path)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Single-Hop/4"):
        return native_hybrid_4_or_16(rel_path, high_join=True)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Single-Hop/5"):
        return native_hybrid_5(rel_path)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Single-Hop/6"):
        return native_hybrid_6(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Hop/13"):
        return native_hybrid_1_or_13(rel_path, high_join=False)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Hop/14"):
        return native_hybrid_2_or_14(rel_path, high_join=False)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Hop/15"):
        return native_hybrid_15(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/16"):
        return native_hybrid_4_or_16(rel_path, high_join=False)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/17"):
        return native_hybrid_17(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Multi-Subgraph Single/18"):
        return native_hybrid_18(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Multi-Hop/19"):
        return native_hybrid_19(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Multi-Hop/20"):
        return native_hybrid_20(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Multi-Hop/21"):
        return native_hybrid_21(rel_path)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Multi-Hop/7"):
        return native_hybrid_7(rel_path)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Multi-Hop/8"):
        return native_hybrid_8_or_9(rel_path, normalized=False)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Multi-Hop/9"):
        return native_hybrid_8_or_9(rel_path, normalized=True)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Single-Hop/10"):
        return native_hybrid_10_11_12(rel_path)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Single-Hop/11"):
        return native_hybrid_10_11_12(rel_path)
    if rel_path.startswith("High_Join_Relational_Graph_Hybrid_Queries/High-Join Single-Subgraph Single-Hop/12"):
        return native_hybrid_10_11_12(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Single-Hop/22"):
        return native_hybrid_22_23_24(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Single-Hop/23"):
        return native_hybrid_22_23_24(rel_path)
    if rel_path.startswith("Low_Join_Relational_Graph_Hybrid_Queries/Low-Join Single-Subgraph Single-Hop/24"):
        return native_hybrid_22_23_24(rel_path)
    return None


def rewrite_one(src: Path) -> manual.RewriteResult:
    rel_path = str(src.relative_to(manual.SOURCE_ROOT))
    if rel_path.startswith("Pure_Graph_Queries/"):
        native = native_pure_graph(rel_path)
        if native is not None:
            return native
    native = native_hybrid(rel_path)
    if native is not None:
        return native
    result = manual.rewrite_one(src)
    if rel_path.startswith("Shortest_Path_Queries/"):
        result.method = "native_" + result.method.removeprefix("manual_")
    return result


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)

    manifest: List[Dict[str, str]] = []
    failures: List[str] = []
    for src in manual.source_sql_files():
        rel_path = str(src.relative_to(manual.SOURCE_ROOT))
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
        "# OrientDB native graph sciscinet rewrites\n\n"
        f"Generated at: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Source root: `{manual.SOURCE_ROOT}`\n\n"
        "This directory prefers OrientDB native graph syntax for graph-heavy SQL/PGQ "
        "queries. Pure graph fixed-path queries are rewritten to `MATCH`; shortest "
        "path queries use OrientDB's `shortestPath()` function. Other query families "
        "fall back to the existing manual OrientDB-compatible rewrites.\n\n"
        "Hybrid graph/relational queries remain conservative fallbacks unless their "
        "graph portion can be separated without changing aggregate or optional-join "
        "semantics.\n",
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
