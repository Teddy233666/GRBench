#!/usr/bin/env bash

set -uo pipefail
RUNNER_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
QUERY_ROOT="$RUNNER_DIR/../../queries"
SUITE_NAME="main"
RUNS=3
REQUIRE_AGE=1
UPDATE_MODE=0
DEFAULT_RESULT_FILE=".local/results/postgresql/main_three_rounds.csv"
QUERY_DIRS=(
  "$QUERY_ROOT/High_Join_Relational_Graph_Hybrid_Queries"
  "$QUERY_ROOT/Low_Join_Relational_Graph_Hybrid_Queries"
  "$QUERY_ROOT/Pure_Graph_Queries"
)

source "$RUNNER_DIR/postgresql_benchmark_common.sh"
run_postgresql_benchmark "$@"
