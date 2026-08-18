#!/usr/bin/env python3
"""Generate a conservative OrientDB-compatible GRBench query directory.

The generator only writes SQL files when the rewrite is known to preserve the
original query semantics in OrientDB 3.2 syntax. Queries that need unsupported
SQL/PGQ table functions, ANSI joins, open-ended shortest paths, or edge
insert-select semantics are recorded in the manifest but are not replaced by
different placeholder SQL.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
SOURCE_ROOT = REPO_ROOT / "benchmark" / "queries" / "canonical"
OUTPUT_ROOT = ROOT / "generated" / "conservative-queries"


@dataclass
class Rewrite:
    status: str
    sql: str = ""
    reason: str = ""
    method: str = ""


def clean_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip())


def unsupported(sql: str) -> str:
    u = sql.upper()
    if "ANY SHORTEST" in u:
        return (
            "SQL/PGQ ANY SHORTEST with a predicate-defined destination has no "
            "direct single-statement OrientDB 3.2 equivalent."
        )
    if "GRAPH_TABLE" in u and (" JOIN " in u or u.count("GRAPH_TABLE") > 1):
        return (
            "The query combines SQL/PGQ GRAPH_TABLE results with SQL JOIN "
            "semantics. A safe rewrite needs a per-template relational-to-MATCH "
            "translation; no semantics-preserving automatic rewrite was emitted."
        )
    if " JOIN " in u:
        return (
            "OrientDB 3.2 SQL does not support ANSI JOIN. A safe rewrite would "
            "need query-specific MATCH/LET decomposition."
        )
    if "GRAPH_TABLE" in u:
        return "This GRAPH_TABLE pattern was not in the verified rewrite set."
    if "INSERT INTO" in u and "SELECT" in u:
        return (
            "INSERT ... SELECT into edge classes cannot be rewritten safely "
            "without creating graph edges from source and destination vertices."
        )
    return "No verified semantics-preserving OrientDB rewrite rule matched."


def update_rewrite(rel_path: str, sql: str) -> Optional[Rewrite]:
    rewrites: Dict[str, str] = {
        "update/Update/1a.sql": """DELETE FROM Papers
WHERE year BETWEEN 2020 AND 2025 UNSAFE;
""",
        "update/Update/1b.sql": """INSERT INTO Papers
SELECT *
FROM grbench_update1_papers;
""",
        "update/Update/2a.sql": """DELETE EDGE PaperReferences
WHERE [citing_paperid, cited_paperid] IN (
    SELECT [citing_paperid, cited_paperid]
    FROM grbench_update2_edges
);
""",
        "update/Update/3a.sql": """DELETE EDGE PaperReferences
WHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers)
   OR cited_paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Papers_to_Authors
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE contributed_from
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE PaperFields
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Link_NSF
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Link_NIH
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Link_ClinicalTrials
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE link_newsfeed
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE link_twitter
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Papers
WHERE year BETWEEN 2020 AND 2025 UNSAFE;
""",
        "update/Update/4a.sql": """DELETE FROM Authors_Gender
WHERE h_index BETWEEN 10 AND 20 UNSAFE;
""",
        "update/Update/4b.sql": """INSERT INTO Authors_Gender
SELECT *
FROM grbench_update4_authors_gender;
""",
        "update/Update/5a.sql": """DELETE EDGE Papers_to_Authors
WHERE [paperid, authorid] IN (
    SELECT [paperid, authorid]
    FROM grbench_update5_papers_to_authors
);
""",
        "update/Update/6a.sql": """DELETE EDGE Papers_to_Authors
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);

DELETE EDGE affiliated_with
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);

DELETE FROM Authors_Gender
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender) UNSAFE;
""",
    }
    if rel_path in rewrites:
        return Rewrite(
            status="REWRITTEN",
            sql=rewrites[rel_path],
            method="update_delete_or_vertex_insert",
            reason="Rewritten to OrientDB DELETE EDGE / DELETE ... UNSAFE or retained INSERT ... SELECT for vertex classes.",
        )
    if rel_path.startswith("update/"):
        return Rewrite(status="NOT_REWRITABLE_EQUIVALENTLY", reason=unsupported(sql))
    return None


def graph_match_select(match: str, projection: str, alias: str = "") -> str:
    select_alias = f" AS {alias}" if alias else ""
    return f"""SELECT
    MIN({projection}){select_alias}
FROM (
    {match}
);
"""


def pure_graph_rewrite(rel_path: str, sql: str) -> Optional[Rewrite]:
    m = re.search(r"(\d+)([abc])\.sql$", rel_path)
    if not m:
        return None
    number = int(m.group(1))
    variant = m.group(2)

    if rel_path.startswith("Pure_Graph_Queries/25"):
        threshold = {"a": None, "b": 1000, "c": 1500}[variant]
        tail = "{as:inst3}"
        if threshold is not None:
            tail = f"{{as:inst3, where:(h_index >= {threshold})}}"
        match = (
            "MATCH {class:Affiliations, as:inst0, where:(institutionid LIKE 'I42101230%')}"
            ".out('affl_assoc_affl'){as:inst1}"
            ".out('affl_assoc_affl'){as:inst2}"
            f".out('affl_assoc_affl'){tail} "
            "RETURN inst0.institutionid AS inst_0_institutionid"
        )
        return Rewrite(
            status="REWRITTEN",
            sql=graph_match_select(match, "inst_0_institutionid"),
            method="verified_single_graph_table",
            reason="Single SQL/PGQ GRAPH_TABLE fixed-path pattern rewritten to OrientDB MATCH.",
        )

    if rel_path.startswith("Pure_Graph_Queries/26"):
        op = {"a": "<=3", "b": "<=1", "c": "=2"}[variant]
        match = (
            "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}.out('Link_NIH'){{as:n}} "
            "RETURN p.paperid AS paperid"
        )
        return Rewrite(
            status="REWRITTEN",
            sql=graph_match_select(match, "paperid", "cited_paperid"),
            method="verified_single_graph_table",
            reason="Single SQL/PGQ GRAPH_TABLE fixed-path pattern rewritten to OrientDB MATCH.",
        )

    if rel_path.startswith("Pure_Graph_Queries/29"):
        threshold = {"a": None, "b": 1000, "c": 1000}[variant]
        m2 = "{as:m2}"
        if threshold is not None:
            m2 = f"{{as:m2, where:(h_index >= {threshold})}}"
        match = (
            "MATCH {class:Affiliations, as:inst, where:(institutionid LIKE 'I42101230%')}"
            ".out('affl_assoc_affl'){as:m1}"
            f".out('affl_assoc_affl'){m2}"
            ".out('affl_assoc_affl'){as:m3}"
            ".out('affl_assoc_affl'){as:assoc} "
            "RETURN assoc.institutionid AS associated_institutionid"
        )
        return Rewrite(
            status="REWRITTEN",
            sql=graph_match_select(match, "associated_institutionid", "associated_institutionid"),
            method="verified_single_graph_table",
            reason="Single SQL/PGQ GRAPH_TABLE fixed-path pattern rewritten to OrientDB MATCH.",
        )

    if rel_path.startswith("Pure_Graph_Queries/30"):
        op = {"a": "<=3", "b": "<=1", "c": "=1"}[variant]
        match = (
            "MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' "
            f"AND citation_count {op})}}.out('Link_NSF'){{as:n}} "
            "RETURN p.paperid AS paperid"
        )
        return Rewrite(
            status="REWRITTEN",
            sql=graph_match_select(match, "paperid", "cited_paperid"),
            method="verified_single_graph_table",
            reason="Single SQL/PGQ GRAPH_TABLE fixed-path pattern rewritten to OrientDB MATCH.",
        )

    return None


def rewrite_query(rel_path: str, sql: str) -> Rewrite:
    for fn in (update_rewrite, pure_graph_rewrite):
        rewritten = fn(rel_path, sql)
        if rewritten is not None:
            return rewritten
    return Rewrite(status="NOT_REWRITABLE_EQUIVALENTLY", reason=unsupported(sql))


def source_sql_files(root: Path) -> Iterable[Path]:
    return sorted(root.rglob("*.sql"), key=lambda p: str(p.relative_to(root)))


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)

    manifest = []
    for src in source_sql_files(SOURCE_ROOT):
        rel_path = str(src.relative_to(SOURCE_ROOT))
        sql = src.read_text(errors="replace")
        rewritten = rewrite_query(rel_path, sql)
        row = {
            "sql_file": rel_path,
            "status": rewritten.status,
            "method": rewritten.method,
            "reason": rewritten.reason,
            "source_path": str(src),
            "output_path": "",
        }
        if rewritten.status == "REWRITTEN":
            out = OUTPUT_ROOT / rel_path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(rewritten.sql, encoding="utf-8")
            row["output_path"] = str(out)
        manifest.append(row)

    headers = ["sql_file", "status", "method", "reason", "source_path", "output_path"]
    with (OUTPUT_ROOT / "rewrite_manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(manifest)

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(SOURCE_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "total_sql": len(manifest),
        "rewritten_sql": sum(1 for row in manifest if row["status"] == "REWRITTEN"),
        "not_rewritable_equivalently": sum(
            1 for row in manifest if row["status"] == "NOT_REWRITABLE_EQUIVALENTLY"
        ),
        "policy": "Only write SQL files for verified semantics-preserving OrientDB 3.2 rewrites.",
    }
    (OUTPUT_ROOT / "rewrite_manifest.json").write_text(
        json.dumps({"metadata": metadata, "queries": manifest}, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "README.md").write_text(
        "\n".join(
            [
                "# OrientDB GRBench query rewrites",
                "",
                "Generated from `benchmark/queries/canonical`.",
                "",
                "Only SQL files with verified semantics-preserving OrientDB 3.2 rewrites are present.",
                "Queries that could not be safely rewritten are listed in `rewrite_manifest.csv`.",
                "",
                f"Total source SQL: {metadata['total_sql']}",
                f"Rewritten SQL files: {metadata['rewritten_sql']}",
                f"Not rewritten: {metadata['not_rewritable_equivalently']}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
