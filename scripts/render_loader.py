#!/usr/bin/env python3
"""Render a historical loader template with repository-local data paths."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SF_PATTERN = re.compile(r"sf10_[0-4]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--sf", choices=[f"sf10_{i}" for i in range(5)], required=True)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / "data" / "processed")),
    )
    parser.add_argument(
        "--prepared-root",
        type=Path,
        default=REPO_ROOT / ".local" / "prepared",
        help="Root for engine-specific preprocessed CSVs such as PostgreSQL AGE inputs.",
    )
    parser.add_argument(
        "--update-root",
        type=Path,
        default=Path(os.environ.get("GRBENCH_UPDATE_DIR", REPO_ROOT / ".local" / "update-staging")),
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def render(text: str, sf: str, data_root: Path, prepared_root: Path, update_root: Path) -> str:
    data_dir = (data_root / sf).resolve()
    prepared_dir = (prepared_root / f"{sf}_postgresql").resolve()
    update_dir = update_root.resolve()

    replacements = {
        "{{DATA_DIR}}": data_dir.as_posix(),
        "{{PREPARED_DIR}}": prepared_dir.as_posix(),
        "{{PREPARED_DOUBLE_DIR}}": (
            prepared_root / f"{sf}_postgresql_postgresql"
        ).resolve().as_posix(),
        "{{UPDATE_DIR}}": update_dir.as_posix(),
    }
    for token, value in replacements.items():
        text = text.replace(token, value)
    text = re.sub(r"\.local/data/sf10_[0-4]", data_dir.as_posix(), text)
    text = re.sub(r"data/processed/sf10_[0-4]", data_dir.as_posix(), text)
    return SF_PATTERN.sub(sf, text)


def main() -> int:
    args = parse_args()
    if not args.template.is_file():
        raise SystemExit(f"loader template not found: {args.template}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = render(
        args.template.read_text(encoding="utf-8"),
        args.sf,
        args.data_root,
        args.prepared_root,
        args.update_root,
    )
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
