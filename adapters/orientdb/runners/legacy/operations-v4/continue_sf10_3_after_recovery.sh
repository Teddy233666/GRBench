#!/usr/bin/env bash
# Historical one-host recovery procedure. Do not use as a release entry point.
set -euo pipefail

recovery_unit="orientdb-sf10_3-update1-recovery-20260728.service"
recovery_log="results/readiness_v4/sf10_3_update1_crash_recovery_v4_20260728/recovery.log"
ADAPTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REPO_ROOT="$(cd "$ADAPTER_DIR/../.." && pwd)"

while systemctl is-active --quiet "$recovery_unit"; do
    sleep 60
done

if ! grep -q '"restored": true' "$recovery_log"; then
    echo "ABORT: sf10_3 recovery did not verify the baseline" >&2
    exit 2
fi

exec python3 "$ADAPTER_DIR/runners/run_orientdb.py" \
    --sf sf10_3 \
    --category update \
    --query-root "$ADAPTER_DIR/queries" \
    --source-query-root "$REPO_ROOT/benchmark/queries/canonical" \
    --db-dir legacy_host_data/grbench/orientdb_manual_data_loaded \
    --load-mode orientdb_manual_data_loaded_native_graph \
    --execution-mode warm \
    --runs 1 \
    --warmup-runs 0 \
    --expected-results results/duckdb_oracle_all_sf_contract_v3.json \
    --timeout 18000 \
    --update-setup-timeout 18000 \
    --update-recovery-timeout 18000 \
    --update-recovery-max-attempts 12 \
    --update-batch-size 10000 \
    --resource-sample-interval 0.01 \
    --heap '-Xms4g -Xmx64g' \
    --results-dir results/readiness_v4/sf10_3_full_update_acceptance_v4_retry_20260728
