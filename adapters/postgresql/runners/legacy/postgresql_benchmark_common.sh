#!/usr/bin/env bash

# Shared implementation for the retained PostgreSQL/AGE shell runners.
# This file must be sourced by a suite-specific entry point.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "ERROR: source this file from a suite-specific runner" >&2
  exit 2
fi

: "${SUITE_NAME:?SUITE_NAME must be set by the entry point}"
: "${RUNS:?RUNS must be set by the entry point}"
: "${DEFAULT_RESULT_FILE:?DEFAULT_RESULT_FILE must be set by the entry point}"
: "${REQUIRE_AGE:?REQUIRE_AGE must be set by the entry point}"
: "${UPDATE_MODE:?UPDATE_MODE must be set by the entry point}"

POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USERNAME="${POSTGRES_USERNAME:-grbench}"
POSTGRES_DATABASE="${POSTGRES_DATABASE:-grbench}"
GRBENCH_TIMEOUT_S="${GRBENCH_TIMEOUT_S:-18000}"
GRBENCH_SAMPLE_INTERVAL_S="${GRBENCH_SAMPLE_INTERVAL_S:-0.01}"
POSTGRES_PROCESS_PATTERN="${POSTGRES_PROCESS_PATTERN:-^(postgres|postmaster)$}"
POSTGRES_CGROUP_PATH="${POSTGRES_CGROUP_PATH:-}"
RESULT_FILE="${GRBENCH_POSTGRESQL_RESULT:-$DEFAULT_RESULT_FILE}"
STATEMENT_TIMEOUT_MS=$((GRBENCH_TIMEOUT_S * 1000))

if ! [[ "$RUNS" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: RUNS must be a positive integer" >&2
  exit 2
fi
if ! [[ "$GRBENCH_TIMEOUT_S" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: GRBENCH_TIMEOUT_S must be a positive integer" >&2
  exit 2
fi

mkdir -p "$(dirname "$RESULT_FILE")"
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/grbench-postgresql.XXXXXX")
MARKER_SEQUENCE=0
SESSION_STARTED=0

cleanup_postgresql_benchmark() {
  if [[ "$SESSION_STARTED" -eq 1 ]]; then
    printf '\\q\n' >&"$PSQL_IN" 2>/dev/null || true
    wait "$PSQL_COPROC_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup_postgresql_benchmark EXIT INT TERM

next_marker() {
  MARKER_SEQUENCE=$((MARKER_SEQUENCE + 1))
  NEXT_MARKER="__GRBENCH_END_$$_${MARKER_SEQUENCE}__"
}

capture_sql() {
  local sql="$1"
  local marker
  next_marker
  marker="$NEXT_MARKER"
  CAPTURE_OUTPUT=""
  CAPTURE_ERROR=""

  {
    printf '%s\n' "$sql"
    printf '\\echo %s\n' "$marker"
  } >&"$PSQL_IN"

  local line
  while IFS= read -r line <&"$PSQL_OUT"; do
    if [[ "$line" == "$marker" ]]; then
      return 0
    fi
    CAPTURE_OUTPUT+="$line"$'\n'
    if [[ "$line" =~ ^(ERROR|FATAL|PANIC): ]]; then
      CAPTURE_ERROR+="$line "
    fi
  done
  CAPTURE_ERROR+="PostgreSQL session exited before the completion marker. "
  return 1
}

start_postgresql_session() {
  local -a psql_command=(
    psql -X -q -A -P pager=off
    -h "$POSTGRES_HOST" -p "$POSTGRES_PORT"
    -U "$POSTGRES_USERNAME" -d "$POSTGRES_DATABASE"
  )
  local -a connection_environment=(env "PGCONNECT_TIMEOUT=${PGCONNECT_TIMEOUT:-30}")
  if [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
    connection_environment+=("PGPASSWORD=$POSTGRES_PASSWORD")
  fi
  coproc PSQL_COPROC {
    "${connection_environment[@]}" "${psql_command[@]}" 2>&1
  }
  PSQL_IN=${PSQL_COPROC[1]}
  PSQL_OUT=${PSQL_COPROC[0]}
  PSQL_COPROC_PID=$!
  SESSION_STARTED=1

  local init_sql
  init_sql="SET statement_timeout = ${STATEMENT_TIMEOUT_MS};"
  if [[ "$REQUIRE_AGE" -eq 1 ]]; then
    init_sql=$'CREATE EXTENSION IF NOT EXISTS age;\nLOAD '\''age'\'';\nSET search_path = ag_catalog, "$user", public;\n'"$init_sql"
  fi
  capture_sql "$init_sql" || true
  if [[ -n "$CAPTURE_ERROR" ]]; then
    echo "ERROR: PostgreSQL session initialization failed: $CAPTURE_ERROR" >&2
    exit 1
  fi
}

load_sql_file() {
  local file="$1"
  LOADED_SQL=""
  LOAD_SQL_ERROR=""
  if [[ ! -f "$file" ]]; then
    LOAD_SQL_ERROR="query file not found: $file"
    return 1
  fi
  LOADED_SQL=$(<"$file")

  local prepared_root="${GRBENCH_POSTGRES_UPDATE_PREPARED_ROOT:-}"
  if [[ "$LOADED_SQL" == *"{{UPDATE_PREPARED_ROOT}}"* ]]; then
    if [[ -z "$prepared_root" ]]; then
      LOAD_SQL_ERROR="set GRBENCH_POSTGRES_UPDATE_PREPARED_ROOT for Update restore queries"
      return 1
    fi
    LOADED_SQL=${LOADED_SQL//\{\{UPDATE_PREPARED_ROOT\}\}/${prepared_root%/}}
  fi

  local legacy_path_pattern="'[^']*/(grbench_update[^/']+\\.csv)'"
  if [[ "$LOADED_SQL" =~ $legacy_path_pattern ]]; then
    if [[ -z "$prepared_root" ]]; then
      LOAD_SQL_ERROR="set GRBENCH_POSTGRES_UPDATE_PREPARED_ROOT for Update restore queries"
      return 1
    fi
    local escaped_root
    escaped_root=$(printf '%s' "${prepared_root%/}" | sed 's/[&|\\]/\\&/g')
    LOADED_SQL=$(printf '%s' "$LOADED_SQL" | sed -E "s|'[^']*/(grbench_update[^/']+\\.csv)'|'${escaped_root}/\\1'|g")
  fi

  local slash="/"
  local home_prefix="${slash}home${slash}"
  local workspace_prefix="${slash}workspace${slash}"
  if [[ "$LOADED_SQL" == *"$home_prefix"* || "$LOADED_SQL" == *"$workspace_prefix"* ]]; then
    LOAD_SQL_ERROR="query still contains a host-specific path after rendering: $file"
    return 1
  fi
}

monitor_postgresql() {
  local logfile="$1"
  local flag_file="$2"
  : > "$logfile"
  while [[ -f "$flag_file" ]]; do
    local cpu mem_kib mem_bytes
    cpu=$(ps -eo %cpu=,comm= | awk -v pattern="$POSTGRES_PROCESS_PATTERN" '$2 ~ pattern {sum += $1} END {print sum + 0}')
    mem_bytes=""
    if [[ -n "$POSTGRES_CGROUP_PATH" && -r "$POSTGRES_CGROUP_PATH/memory.current" ]]; then
      mem_bytes=$(<"$POSTGRES_CGROUP_PATH/memory.current")
    elif [[ -n "$POSTGRES_CGROUP_PATH" && -r "$POSTGRES_CGROUP_PATH/memory/memory.usage_in_bytes" ]]; then
      mem_bytes=$(<"$POSTGRES_CGROUP_PATH/memory/memory.usage_in_bytes")
    fi
    if [[ -n "$mem_bytes" ]]; then
      mem_kib=$(awk -v bytes="$mem_bytes" 'BEGIN {printf "%.6f", bytes / 1024}')
    else
      mem_kib=$(ps -eo rss=,comm= | awk -v pattern="$POSTGRES_PROCESS_PATTERN" '$2 ~ pattern {sum += $1} END {print sum + 0}')
    fi
    printf '%s,%s\n' "$cpu" "$mem_kib" >> "$logfile"
    sleep "$GRBENCH_SAMPLE_INTERVAL_S"
  done
}

calculate_stats() {
  local logfile="$1"
  awk -F',' '
    NF >= 2 {
      cpu_sum += $1; mem_sum += $2; count++
      if ($1 > cpu_peak) cpu_peak = $1
      if ($2 > mem_peak) mem_peak = $2
    }
    END {
      if (count == 0) { print "0.000 0.000 0.000 0.000 0"; exit }
      printf "%.3f %.3f %.3f %.3f %d", cpu_peak, cpu_sum/count, mem_peak/1024, (mem_sum/count)/1024, count
    }
  ' "$logfile"
}

elapsed_seconds() {
  awk -v start="$1" -v finish="$2" 'BEGIN {printf "%.6f", finish - start}'
}

normalize_output() {
  printf '%s' "$1" | tr '\n' ' ' | sed 's/"/""/g; s/[[:space:]][[:space:]]*/ /g'
}

set_failed_result() {
  SQL_ELAPSED="0.000000"
  SQL_CPU_PEAK="0.000"
  SQL_CPU_AVG="0.000"
  SQL_MEM_PEAK="0.000"
  SQL_MEM_AVG="0.000"
  SQL_SAMPLE_COUNT="0"
  SQL_STATUS="$1"
  SQL_OUTPUT=""
  SQL_ERROR="$2"
}

run_sql_file() {
  local file="$1"
  local setup_file="${2:-}"
  if ! load_sql_file "$file"; then
    set_failed_result "FAILED" "$LOAD_SQL_ERROR"
    return
  fi
  local measured_sql="$LOADED_SQL"
  local in_transaction=0

  if [[ "$UPDATE_MODE" -eq 1 ]]; then
    capture_sql "BEGIN;" || true
    if [[ -n "$CAPTURE_ERROR" ]]; then
      set_failed_result "SETUP_ERROR" "$CAPTURE_ERROR"
      return
    fi
    in_transaction=1
    if [[ -n "$setup_file" ]]; then
      if ! load_sql_file "$setup_file"; then
        capture_sql "ROLLBACK;" || true
        set_failed_result "SETUP_ERROR" "$LOAD_SQL_ERROR"
        return
      fi
      capture_sql "$LOADED_SQL" || true
      if [[ -n "$CAPTURE_ERROR" ]]; then
        local setup_error="$CAPTURE_ERROR"
        capture_sql "ROLLBACK;" || true
        set_failed_result "SETUP_ERROR" "$setup_error"
        return
      fi
    fi
  fi

  local monitor_log="$TMP_DIR/monitor.$$.${MARKER_SEQUENCE}.csv"
  local flag_file="$TMP_DIR/monitor.$$.${MARKER_SEQUENCE}.flag"
  : > "$flag_file"
  monitor_postgresql "$monitor_log" "$flag_file" &
  local monitor_pid=$!
  local started finished
  started=$(date +%s.%N)
  capture_sql "$measured_sql" || true
  finished=$(date +%s.%N)
  rm -f "$flag_file"
  wait "$monitor_pid" 2>/dev/null || true

  SQL_ELAPSED=$(elapsed_seconds "$started" "$finished")
  read -r SQL_CPU_PEAK SQL_CPU_AVG SQL_MEM_PEAK SQL_MEM_AVG SQL_SAMPLE_COUNT < <(calculate_stats "$monitor_log")
  SQL_OUTPUT=$(normalize_output "$CAPTURE_OUTPUT")
  SQL_ERROR="$CAPTURE_ERROR"
  if [[ "$SQL_ERROR" == *"statement timeout"* || "$SQL_ERROR" == *"canceling statement"* ]]; then
    SQL_STATUS="TIMEOUT"
  elif [[ -n "$SQL_ERROR" ]]; then
    SQL_STATUS="FAILED"
  else
    SQL_STATUS="OK"
  fi

  if [[ "$in_transaction" -eq 1 ]]; then
    capture_sql "ROLLBACK;" || true
    if [[ -n "$CAPTURE_ERROR" && "$SQL_STATUS" == "OK" ]]; then
      SQL_STATUS="ROLLBACK_ERROR"
      SQL_ERROR="$CAPTURE_ERROR"
    fi
  fi
}

collect_query_files() {
  SQL_FILES=()
  local directory
  for directory in "${QUERY_DIRS[@]}"; do
    if [[ ! -d "$directory" ]]; then
      echo "ERROR: query directory not found: $directory" >&2
      exit 1
    fi
    while IFS= read -r -d '' file; do
      SQL_FILES+=("$file")
    done < <(find "$directory" -type f -name '*.sql' -print0 | sort -z -V)
  done
  if [[ "${#SQL_FILES[@]}" -eq 0 ]]; then
    echo "ERROR: no SQL files found for $SUITE_NAME" >&2
    exit 1
  fi
}

paired_setup_file() {
  local file="$1"
  local stem
  stem=$(basename "$file" .sql)
  if [[ "$UPDATE_MODE" -eq 1 && "$stem" =~ ^([1-6])b$ ]]; then
    printf '%s/%sa.sql' "$(dirname "$file")" "${BASH_REMATCH[1]}"
  fi
}

csv_escape() {
  local value="$1"
  value=${value//\"/\"\"}
  printf '"%s"' "$value"
}

run_postgresql_benchmark() {
  collect_query_files
  case "${1:-}" in
    --help)
      echo "usage: $(basename "$0") [--list]"
      echo "  --list  print the ordered query inventory without opening PostgreSQL"
      return 0
      ;;
    --list)
      echo "suite=$SUITE_NAME runs=$RUNS queries=${#SQL_FILES[@]}"
      printf '%s\n' "${SQL_FILES[@]}"
      return 0
      ;;
    "")
      ;;
    *)
      echo "ERROR: unsupported argument: $1" >&2
      return 2
      ;;
  esac
  start_postgresql_session
  echo "suite=$SUITE_NAME runs=$RUNS queries=${#SQL_FILES[@]} database=$POSTGRES_DATABASE"
  echo "results=$RESULT_FILE"

  declare -A ELAPSED CPU_PEAK CPU_AVG MEM_PEAK MEM_AVG SAMPLE_COUNT STATUS OUTPUT ERROR
  local run file key setup_file
  for ((run=1; run<=RUNS; run++)); do
    echo "round=$run/$RUNS"
    for file in "${SQL_FILES[@]}"; do
      setup_file=$(paired_setup_file "$file")
      run_sql_file "$file" "$setup_file"
      key="$file|$run"
      ELAPSED["$key"]="$SQL_ELAPSED"
      CPU_PEAK["$key"]="$SQL_CPU_PEAK"
      CPU_AVG["$key"]="$SQL_CPU_AVG"
      MEM_PEAK["$key"]="$SQL_MEM_PEAK"
      MEM_AVG["$key"]="$SQL_MEM_AVG"
      SAMPLE_COUNT["$key"]="$SQL_SAMPLE_COUNT"
      STATUS["$key"]="$SQL_STATUS"
      OUTPUT["$key"]="$SQL_OUTPUT"
      ERROR["$key"]="$SQL_ERROR"
      echo "query=$(basename "$file") status=$SQL_STATUS elapsed=$SQL_ELAPSED"
    done
  done

  echo "sql_file,time_sec,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,sample_count,selected_run,status,result,error" > "$RESULT_FILE"
  local selected
  for file in "${SQL_FILES[@]}"; do
    selected=$(
      for ((run=1; run<=RUNS; run++)); do
        key="$file|$run"
        printf '%s\t%s\n' "${ELAPSED[$key]}" "$run"
      done | sort -n -k1,1 -k2,2 | awk -v count="$RUNS" 'NR == int((count + 1) / 2) {print $2}'
    )
    key="$file|$selected"
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$(csv_escape "$file")" \
      "${ELAPSED[$key]}" "${CPU_PEAK[$key]}" "${CPU_AVG[$key]}" \
      "${MEM_PEAK[$key]}" "${MEM_AVG[$key]}" "${SAMPLE_COUNT[$key]}" "$selected" \
      "${STATUS[$key]}" "$(csv_escape "${OUTPUT[$key]}")" "$(csv_escape "${ERROR[$key]}")" \
      >> "$RESULT_FILE"
  done
  echo "benchmark complete: $RESULT_FILE"
}
