"""Shared repetition and result-selection rules for Kuzu benchmark runners."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Iterable


TERMINAL_STATUSES = {"TIMEOUT", "PROCESS_EXITED"}


def validate_run_counts(warmups: int, repeats: int) -> None:
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    if repeats < 1 or repeats % 2 == 0:
        raise ValueError("repeats must be a positive odd number")


def _elapsed(run: dict[str, Any]) -> float:
    return float(run.get("elapsed_s") or 0.0)


def select_median_elapsed_run(
    runs: list[dict[str, Any]],
    *,
    warmups_requested: int,
    warmups_completed: int,
    repeats_requested: int,
) -> dict[str, Any]:
    if not runs:
        raise ValueError("at least one measured run is required")

    terminal_index = next(
        (
            index
            for index, run in enumerate(runs)
            if run.get("status") in TERMINAL_STATUSES
        ),
        None,
    )
    selected_index = (
        terminal_index
        if terminal_index is not None
        else sorted(range(len(runs)), key=lambda index: (_elapsed(runs[index]), index))[
            len(runs) // 2
        ]
    )
    selected = dict(runs[selected_index])
    statuses = [str(run.get("status", "")) for run in runs]
    result_signatures = [
        (
            run.get("status"),
            run.get("rows"),
            run.get("result"),
            "" if run.get("status") == "OK" else run.get("error"),
        )
        for run in runs
    ]
    consistent = (
        len(runs) == repeats_requested
        and warmups_completed == warmups_requested
        and len(set(statuses)) == 1
        and len(set(result_signatures)) == 1
    )
    terminal_status = str(runs[selected_index].get("status", "")) if terminal_index is not None else ""
    if terminal_status:
        selected["status"] = terminal_status
        selected["error"] = next(
            (
                str(run.get("error", ""))
                for run in runs
                if run.get("status") == terminal_status
            ),
            "",
        )
    elif not consistent:
        selected["status"] = "REPEAT_MISMATCH"
        selected["error"] = (
            "Measured repetitions returned inconsistent statuses or results: "
            + ",".join(statuses)
        )

    selected.update(
        {
            "warmup_runs": warmups_requested,
            "warmup_runs_completed": warmups_completed,
            "measured_runs": repeats_requested,
            "measured_runs_completed": len(runs),
            "selected_measured_run": selected_index + 1,
            "measured_elapsed_s": ";".join(f"{_elapsed(run):.9f}" for run in runs),
            "measured_statuses": ";".join(statuses),
            "repeat_consistent": str(consistent).lower(),
        }
    )
    return selected


def run_repeated(
    run_once: Callable[[], dict[str, Any]],
    *,
    warmups: int = 1,
    repeats: int = 3,
) -> dict[str, Any]:
    validate_run_counts(warmups, repeats)
    warmups_completed = 0
    for _ in range(warmups):
        warmup = run_once()
        warmups_completed += 1
        if warmup.get("status") in TERMINAL_STATUSES:
            out = dict(warmup)
            out.update(
                {
                    "warmup_runs": warmups,
                    "warmup_runs_completed": warmups_completed,
                    "measured_runs": repeats,
                    "measured_runs_completed": 0,
                    "selected_measured_run": "",
                    "measured_elapsed_s": "",
                    "measured_statuses": "",
                    "repeat_consistent": "false",
                }
            )
            return out

    measured = []
    for _ in range(repeats):
        run = run_once()
        measured.append(run)
        if run.get("status") in TERMINAL_STATUSES:
            break
    return select_median_elapsed_run(
        measured,
        warmups_requested=warmups,
        warmups_completed=warmups_completed,
        repeats_requested=repeats,
    )


def ensure_csv_schema(path: Path, columns: Iterable[str]) -> None:
    expected = list(columns)
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open(newline="", encoding="utf-8") as handle:
        actual = csv.DictReader(handle).fieldnames or []
    if actual != expected:
        raise ValueError(
            f"Refusing to append to incompatible result schema at {path}. "
            "Use a new path or --overwrite."
        )
