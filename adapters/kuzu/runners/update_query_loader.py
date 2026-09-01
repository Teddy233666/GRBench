"""Load and render the file-backed Kuzu Update query definitions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


STATEMENT_MARKER = "-- statement"
TOKEN_RE = re.compile(r"{{([A-Z0-9_]+)}}")


def _required_string(entry: dict[str, Any], field: str, manifest_path: Path) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{manifest_path}: query entry requires non-empty {field!r}")
    return value


def split_statement_template(template: str, source: Path) -> list[str]:
    """Split a template on explicit marker lines without parsing Cypher syntax."""
    statements: list[str] = []
    current: list[str] = []
    saw_marker = False
    for line in template.splitlines():
        if line.strip() == STATEMENT_MARKER:
            saw_marker = True
            statement = "\n".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue
        current.append(line)
    statement = "\n".join(current).strip()
    if statement:
        statements.append(statement)
    if not saw_marker or not statements:
        raise ValueError(f"{source}: expected one or more {STATEMENT_MARKER!r} sections")
    return statements


def render_statements(
    template: str,
    variables: Mapping[str, str | Path],
    source: Path,
) -> list[str]:
    values = {name.upper(): str(value) for name, value in variables.items()}
    required = set(TOKEN_RE.findall(template))
    missing = sorted(required - set(values))
    if missing:
        raise ValueError(f"{source}: missing template value(s): {', '.join(missing)}")
    rendered = TOKEN_RE.sub(lambda match: values[match.group(1)], template)
    return split_statement_template(rendered, source)


def load_update_tasks(
    query_root: Path,
    variables: Mapping[str, str | Path],
) -> list[dict[str, Any]]:
    """Load the Update inventory and resolve setup-query references."""
    manifest_path = query_root / "manifest.json"
    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Kuzu Update manifest not found: {manifest_path}") from exc
    if not isinstance(entries, list):
        raise ValueError(f"{manifest_path}: top-level JSON value must be a list")

    tasks: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{manifest_path}: every query entry must be an object")
        query_id = _required_string(entry, "query_id", manifest_path)
        if query_id in by_id:
            raise ValueError(f"{manifest_path}: duplicate query_id {query_id!r}")
        template_path = query_root / _required_string(entry, "template", manifest_path)
        statements = render_statements(
            template_path.read_text(encoding="utf-8"),
            variables,
            template_path,
        )
        task = {
            "query_id": query_id,
            "sql_file": _required_string(entry, "sql_file", manifest_path),
            "description": _required_string(entry, "description", manifest_path),
            "statements": statements,
            "setup_query": entry.get("setup_query"),
            "query_path": template_path,
        }
        tasks.append(task)
        by_id[query_id] = task

    for task in tasks:
        setup_query = task.pop("setup_query")
        if setup_query is None:
            task["setup"] = []
            continue
        if not isinstance(setup_query, str) or setup_query not in by_id:
            raise ValueError(
                f"{manifest_path}: {task['query_id']} references unknown setup_query {setup_query!r}"
            )
        if setup_query == task["query_id"]:
            raise ValueError(f"{manifest_path}: {task['query_id']} cannot set itself up")
        task["setup"] = list(by_id[setup_query]["statements"])

    return tasks
