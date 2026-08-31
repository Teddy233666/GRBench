#!/usr/bin/env bash
# Historical Contract-v4 procedure. It predates the public 123-query contract.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REPO_ROOT="$(cd "$ROOT/../.." && pwd)"
DB_DIR="legacy_host_data/grbench/orientdb_manual_data_loaded"
QUERY_ROOT="$ROOT/queries"
SOURCE_QUERY_ROOT="$REPO_ROOT/benchmark/queries/canonical"
ORACLE="$ROOT/results/duckdb_oracle_all_sf_contract_v3.json"
STAMP="${STAMP:-$(date '+%Y%m%d_%H%M%S')}"
RESULT_BASE="$ROOT/results/formal_contract_v4_sf10_0_to_sf10_3_$STAMP"
LOG_DIR="$ROOT/logs/formal_contract_v4_sf10_0_to_sf10_3_$STAMP"
PREFLIGHT_DIR="${RESULT_BASE}_preflight"
READS_DIR="${RESULT_BASE}_reads"
UPDATES_DIR="${RESULT_BASE}_updates"

log() {
    printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

refuse_resource_competition() {
    local pattern
    pattern='OrientDbCsvLoader|load_orientdb_data[.]py|OrientDbBenchmarkWorker|OConsoleDatabaseApp|run_orientdb[.]py'
    if systemctl is-active --quiet orientdb-sf10-3-rebuild-20260804.service; then
        printf 'ABORT: sf10_3 rebuild service is still active\n' >&2
        exit 2
    fi
    if pgrep -f "$pattern" >/dev/null; then
        printf 'ABORT: another OrientDB loader, recovery, or benchmark process is active\n' >&2
        pgrep -af "$pattern" >&2 || true
        exit 2
    fi
}

require_fresh_outputs() {
    local path
    for path in \
        "$RESULT_BASE-input-audit.json" \
        "$PREFLIGHT_DIR" \
        "$READS_DIR" \
        "$UPDATES_DIR" \
        "$LOG_DIR"; do
        if [[ -e "$path" ]]; then
            printf 'ABORT: output path already exists: %s\n' "$path" >&2
            exit 2
        fi
    done
}

exec 9>/run/lock/orientdb-grbench-formal.lock
if ! flock -n 9; then
    printf 'ABORT: another formal OrientDB pipeline holds the benchmark lock\n' >&2
    exit 2
fi

refuse_resource_competition
require_fresh_outputs
mkdir -p "$LOG_DIR"

log "Running database-free formal input audit"
python3 "$ROOT/tools/audit_orientdb_formal_inputs.py" \
    --output "$RESULT_BASE-input-audit.json" \
  >"$LOG_DIR/input_audit.log" 2>&1

log "Running strict preflight for sf10_0 through sf10_3"
refuse_resource_competition
python3 "$ROOT/runners/run_orientdb.py" \
    --sf sf10_0 --sf sf10_1 --sf sf10_2 --sf sf10_3 \
    --query-root "$QUERY_ROOT" \
    --source-query-root "$SOURCE_QUERY_ROOT" \
    --db-dir "$DB_DIR" \
    --load-mode orientdb_manual_data_loaded_native_graph \
    --expected-results "$ORACLE" \
    --execution-mode warm --heap '-Xms4g -Xmx64g' \
    --timeout 18000 --update-setup-timeout 18000 \
    --update-recovery-timeout 18000 --update-recovery-max-attempts 12 \
    --preflight-only \
    --results-dir "$PREFLIGHT_DIR" \
  >"$LOG_DIR/preflight.log" 2>&1

log "Running 828 formal read-query measurements serially"
refuse_resource_competition
python3 "$ROOT/runners/run_orientdb.py" \
    --sf sf10_0 --sf sf10_1 --sf sf10_2 --sf sf10_3 \
    --stop-before-update \
    --query-root "$QUERY_ROOT" \
    --source-query-root "$SOURCE_QUERY_ROOT" \
    --db-dir "$DB_DIR" \
    --load-mode orientdb_manual_data_loaded_native_graph \
    --expected-results "$ORACLE" \
    --execution-mode warm --runs 3 --warmup-runs 1 \
    --timeout 18000 --resource-sample-interval 0.01 \
    --worker-max-result-rows 10000 --heap '-Xms4g -Xmx64g' \
    --results-dir "$READS_DIR" \
  >"$LOG_DIR/reads.log" 2>&1

log "Building 48-row Update result set: 36 reused rows and 12 fresh sf10_3 rows"
refuse_resource_competition
set +e
python3 "$ROOT/runners/run_orientdb.py" \
    --sf sf10_0 --sf sf10_1 --sf sf10_2 --sf sf10_3 \
    --category update \
    --query-root "$QUERY_ROOT" \
    --source-query-root "$SOURCE_QUERY_ROOT" \
    --db-dir "$DB_DIR" \
    --load-mode orientdb_manual_data_loaded_native_graph \
    --execution-mode warm --runs 1 --warmup-runs 0 \
    --timeout 18000 --update-setup-timeout 18000 \
    --update-recovery-timeout 18000 --update-recovery-max-attempts 12 \
    --update-batch-size 10000 --resource-sample-interval 0.01 \
    --heap '-Xms4g -Xmx64g' \
    --reuse-update-results "$ROOT/results/readiness_v4/sf10_0_full_update_acceptance_v4_20260723" \
    --reuse-update-results "$ROOT/results/readiness_v4/sf10_1_full_update_acceptance_v4_20260723" \
    --reuse-update-results "$ROOT/results/readiness_v4/sf10_2_update1_regression_v4_20260722" \
    --reuse-update-results "$ROOT/results/readiness_v4/sf10_2_update_2_to_6_acceptance_v4_20260723" \
    --results-dir "$UPDATES_DIR" \
  >"$LOG_DIR/updates.log" 2>&1
update_rc=$?
set -e
if (( update_rc != 0 && update_rc != 3 )); then
    printf 'ABORT: Update phase failed with exit code %s\n' "$update_rc" >&2
    exit "$update_rc"
fi

python3 - "$UPDATES_DIR/all_results.csv" <<'PY'
import csv
import sys

path = sys.argv[1]
with open(path, newline="", encoding="utf-8") as stream:
    rows = list(csv.DictReader(stream))

query_paths = [f"update/Update/{number}{suffix}.sql" for number in range(1, 7) for suffix in ("a", "b")]
expected_pairs = {(sf, query) for sf in ("sf10_0", "sf10_1", "sf10_2", "sf10_3") for query in query_paths}
actual_pairs = [(row.get("sf", ""), row.get("sql_file", "")) for row in rows]
if len(rows) != 48 or len(set(actual_pairs)) != 48 or set(actual_pairs) != expected_pairs:
    raise SystemExit("Update result set is not the expected 48 unique rows")

expected_timeouts = {
    ("sf10_2", "update/Update/1a.sql"),
    ("sf10_2", "update/Update/3a.sql"),
}
actual_timeouts = {pair for pair, row in zip(actual_pairs, rows) if row.get("status") == "TIMEOUT"}
unexpected_statuses = [
    f"{sf}:{query}:{row.get('status', '')}"
    for (sf, query), row in zip(actual_pairs, rows)
    if row.get("status") not in ({"TIMEOUT"} if (sf, query) in expected_timeouts else {"OK"})
]
if actual_timeouts != expected_timeouts or unexpected_statuses:
    raise SystemExit(
        f"unexpected Update statuses: timeouts={sorted(actual_timeouts)}, other={unexpected_statuses}"
    )

wrong_origin = [
    f"{sf}:{query}:{row.get('result_origin', '')}"
    for (sf, query), row in zip(actual_pairs, rows)
    if (sf in {"sf10_0", "sf10_1", "sf10_2"})
    != (row.get("result_origin") == "reused_update_acceptance")
]
if wrong_origin:
    raise SystemExit(f"unexpected Update provenance: {wrong_origin}")
PY

if ! jq -e '
    .reused_update_result_count == 36 and
    .strict_execution_status == "FAIL" and
    .strict_execution_failures == [
        "sf10_2:update/Update/1a.sql:TIMEOUT",
        "sf10_2:update/Update/3a.sql:TIMEOUT"
    ]
' "$UPDATES_DIR/metadata.json" >/dev/null; then
    printf 'ABORT: Update metadata contains failures beyond the two preserved sf10_2 timeouts\n' >&2
    exit 3
fi

log "Phase completed"
log "Preflight: $PREFLIGHT_DIR"
log "Reads: $READS_DIR"
log "Updates: $UPDATES_DIR"
log "Logs: $LOG_DIR"
