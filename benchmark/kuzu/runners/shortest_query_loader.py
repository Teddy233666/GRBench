"""Load and render the file-backed Kuzu shortest-path query definitions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEPTH_RANGE_TOKEN = "{{DEPTH_RANGE}}"
UNRESOLVED_TOKEN_RE = re.compile(r"{{[A-Z0-9_]+}}")


def render_exact_depth(template: str, depth: int, source: Path) -> str:
    """Render one exact-depth step without changing the historical Cypher."""
    if depth < 1:
        raise ValueError(f"positive-depth template cannot render depth {depth}: {source}")
    depth_range = "" if depth == 1 else f"*{depth}..{depth}"
    rendered = template.replace(DEPTH_RANGE_TOKEN, depth_range).strip()
    unresolved = sorted(set(UNRESOLVED_TOKEN_RE.findall(rendered)))
    if unresolved:
        raise ValueError(f"unresolved template token(s) in {source}: {', '.join(unresolved)}")
    return rendered


def _required_string(entry: dict[str, Any], field: str, manifest_path: Path) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{manifest_path}: query entry requires non-empty {field!r}")
    return value


def load_shortest_queries(query_root: Path, max_unbounded_depth: int) -> list[dict[str, Any]]:
    """Load the query inventory and expand each query into exact-depth steps."""
    if max_unbounded_depth < 1:
        raise ValueError("max_unbounded_depth must be at least 1")

    manifest_path = query_root / "manifest.json"
    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Kuzu shortest-path manifest not found: {manifest_path}") from exc
    if not isinstance(entries, list):
        raise ValueError(f"{manifest_path}: top-level JSON value must be a list")

    queries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{manifest_path}: every query entry must be an object")
        query_id = _required_string(entry, "query_id", manifest_path)
        if query_id in seen_ids:
            raise ValueError(f"{manifest_path}: duplicate query_id {query_id!r}")
        seen_ids.add(query_id)

        template_path = query_root / _required_string(entry, "template", manifest_path)
        template = template_path.read_text(encoding="utf-8")
        min_depth = entry.get("min_depth")
        max_depth_spec = entry.get("max_depth")
        if not isinstance(min_depth, int) or min_depth < 0:
            raise ValueError(f"{manifest_path}: {query_id} has invalid min_depth")
        if max_depth_spec == "argument":
            max_depth = max_unbounded_depth
        elif isinstance(max_depth_spec, int):
            max_depth = max_depth_spec
        else:
            raise ValueError(f"{manifest_path}: {query_id} has invalid max_depth")
        if max_depth < min_depth:
            raise ValueError(f"{manifest_path}: {query_id} has max_depth below min_depth")

        zero_template = None
        zero_template_name = entry.get("zero_template")
        if zero_template_name is not None:
            if not isinstance(zero_template_name, str) or not zero_template_name:
                raise ValueError(f"{manifest_path}: {query_id} has invalid zero_template")
            zero_path = query_root / zero_template_name
            zero_template = zero_path.read_text(encoding="utf-8").strip()
            unresolved = sorted(set(UNRESOLVED_TOKEN_RE.findall(zero_template)))
            if unresolved:
                raise ValueError(f"unresolved template token(s) in {zero_path}: {', '.join(unresolved)}")
        if min_depth == 0 and zero_template is None:
            raise ValueError(f"{manifest_path}: {query_id} requires zero_template")

        steps = []
        for depth in range(min_depth, max_depth + 1):
            steps.append(zero_template if depth == 0 else render_exact_depth(template, depth, template_path))

        queries.append(
            {
                "category": "Shortest_Path_Queries",
                "subcategory": _required_string(entry, "subcategory", manifest_path),
                "sql_file": _required_string(entry, "sql_file", manifest_path),
                "steps": steps,
                "unbounded": bool(entry.get("unbounded", False)),
                "query_path": template_path,
            }
        )

    return queries
