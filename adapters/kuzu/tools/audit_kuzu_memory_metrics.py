#!/usr/bin/env python3
"""Audit suspicious memory metrics in the combined Kuzu result CSV."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / ".local" / "results" / "kuzu"
DEFAULT_INPUT = RESULTS_DIR / "kuzu_sf10_0_to_sf10_3_all_results.csv"
DEFAULT_SUMMARY = RESULTS_DIR / "kuzu_memory_metrics_audit.csv"
DEFAULT_REPORT = RESULTS_DIR / "kuzu_memory_metrics_audit.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def as_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def mem_pair(row: dict[str, str]) -> tuple[float, float] | None:
    peak = as_float(row.get("mem_peak_mb"))
    avg = as_float(row.get("mem_avg_mb"))
    if peak is None or avg is None:
        return None
    return round(peak, 6), round(avg, 6)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def grouped(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["dataset"], row["suite"]), []).append(row)
    return groups


def group_stats(rows: list[dict[str, str]]) -> dict[str, object]:
    pairs = [mem_pair(row) for row in rows]
    valid = [pair for pair in pairs if pair is not None]
    pair_counts = Counter(valid)
    equal_peak_avg = sum(1 for pair in valid if pair[0] == pair[1])
    repeated_pair_rows = sum(count for count in pair_counts.values() if count > 1)
    adjacent_same_pair = 0
    prev_avg_equals_current_peak = 0
    suspicious_examples = []

    previous_pair = None
    previous_row = None
    for row, pair in zip(rows, pairs):
        if pair is None:
            previous_pair = None
            previous_row = None
            continue
        if previous_pair == pair:
            adjacent_same_pair += 1
            if len(suspicious_examples) < 6:
                suspicious_examples.append(
                    f"{previous_row['sql_file']} -> {row['sql_file']} same pair {pair[0]:.3f}/{pair[1]:.3f}"
                )
        if previous_pair is not None and previous_pair[1] == pair[0]:
            prev_avg_equals_current_peak += 1
            if len(suspicious_examples) < 6:
                suspicious_examples.append(
                    f"{previous_row['sql_file']} avg == {row['sql_file']} peak ({pair[0]:.3f})"
                )
        previous_pair = pair
        previous_row = row

    top_pairs = "; ".join(
        f"{pair[0]:.3f}/{pair[1]:.3f} x{count}"
        for pair, count in pair_counts.most_common(5)
        if count > 1
    )
    return {
        "rows": len(rows),
        "valid_mem_rows": len(valid),
        "equal_peak_avg_rows": equal_peak_avg,
        "equal_peak_avg_pct": round(equal_peak_avg / len(valid) * 100, 2) if valid else 0.0,
        "duplicate_mem_pair_rows": repeated_pair_rows,
        "duplicate_mem_pair_pct": round(repeated_pair_rows / len(valid) * 100, 2) if valid else 0.0,
        "adjacent_same_pair_count": adjacent_same_pair,
        "prev_avg_equals_current_peak_count": prev_avg_equals_current_peak,
        "top_duplicate_pairs": top_pairs,
        "examples": " | ".join(suspicious_examples),
    }


def write_summary(path: Path, stats_rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "dataset",
        "suite",
        "rows",
        "valid_mem_rows",
        "equal_peak_avg_rows",
        "equal_peak_avg_pct",
        "duplicate_mem_pair_rows",
        "duplicate_mem_pair_pct",
        "adjacent_same_pair_count",
        "prev_avg_equals_current_peak_count",
        "top_duplicate_pairs",
        "examples",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(stats_rows)


def md_cell(value: object) -> str:
    return str(value).replace("|", "<br>")


def write_report(path: Path, input_path: Path, summary_path: Path, stats_rows: list[dict[str, object]]) -> None:
    worst = sorted(
        stats_rows,
        key=lambda row: (float(row["duplicate_mem_pair_pct"]), float(row["equal_peak_avg_pct"])),
        reverse=True,
    )[:6]
    lines = [
        "# Kuzu Memory Metrics Audit",
        "",
        f"Input CSV: `{input_path}`",
        f"Summary CSV: `{summary_path}`",
        "",
        "## Finding",
        "",
        "The current `mem_peak_mb` and `mem_avg_mb` columns are not reliable per-query memory metrics. "
        "They were collected as resident memory of the long-lived Python/Kuzu process while one database "
        "object was reused across many queries. The values therefore include Kuzu buffer/cache state and "
        "allocations left by earlier queries.",
        "",
        "This explains the repeated values seen in the Excel file: short queries often have only one or a few "
        "RSS samples, and when the process RSS does not move, peak and average are identical. Consecutive "
        "queries can also inherit the previous steady RSS value, so the previous average can equal the next "
        "peak or average.",
        "",
        "## Highest-Risk Groups",
        "",
        "| Dataset | Suite | Rows | Peak=Avg | Duplicate Pair Rows | Adjacent Same Pair | Examples |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in worst:
        lines.append(
            f"| {row['dataset']} | {row['suite']} | {row['rows']} | "
            f"{row['equal_peak_avg_rows']} ({row['equal_peak_avg_pct']}%) | "
            f"{row['duplicate_mem_pair_rows']} ({row['duplicate_mem_pair_pct']}%) | "
            f"{row['adjacent_same_pair_count']} | {md_cell(row['examples'])} |"
        )
    lines.extend(
        [
            "",
            "## Resolution",
            "",
            "Use per-query process isolation for memory measurements. A corrected run should open Kuzu in a "
            "fresh child process, take `rss_baseline_mb` after database and connection creation, start timing "
            "immediately before the query, and report both absolute process RSS and `mem_*_delta_mb` relative "
            "to that baseline. The existing elapsed-time values remain useful as wall-clock timings, but the "
            "legacy memory columns should not be used for cross-query or cross-SF comparisons.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = read_rows(args.input)
    stats_rows = []
    for (dataset, suite), group_rows in sorted(grouped(rows).items()):
        stats = group_stats(group_rows)
        stats_rows.append({"dataset": dataset, "suite": suite, **stats})
    write_summary(args.summary, stats_rows)
    write_report(args.report, args.input, args.summary, stats_rows)
    print(f"Wrote {args.summary}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
