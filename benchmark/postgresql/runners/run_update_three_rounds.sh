#!/usr/bin/env bash

set -uo pipefail
RUNNER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
QUERY_ROOT="$RUNNER_DIR/../queries"
SUITE_NAME="update"
RUNS=3
REQUIRE_AGE=1
UPDATE_MODE=1
DEFAULT_RESULT_FILE=".local/results/postgresql/update_three_rounds.csv"
QUERY_DIRS=("$QUERY_ROOT/Update")

source "$RUNNER_DIR/postgresql_benchmark_common.sh"
run_postgresql_benchmark "$@"
