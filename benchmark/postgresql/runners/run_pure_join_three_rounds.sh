#!/usr/bin/env bash

set -uo pipefail
RUNNER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
QUERY_ROOT="$RUNNER_DIR/../queries"
SUITE_NAME="pure_join"
RUNS=3
REQUIRE_AGE=0
UPDATE_MODE=0
DEFAULT_RESULT_FILE=".local/results/postgresql/pure_join_three_rounds.csv"
QUERY_DIRS=("$QUERY_ROOT/Pure_Join_Queries")

source "$RUNNER_DIR/postgresql_benchmark_common.sh"
run_postgresql_benchmark "$@"
