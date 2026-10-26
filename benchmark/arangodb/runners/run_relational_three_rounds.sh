#!/usr/bin/env bash

############################################
# CONFIG
############################################

DB_NAME="${ARANGODB_DATABASE:-grbench}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

RESULT_FILE="${GRBENCH_ARANGODB_RESULT:-.local/results/arangodb/relational_three_rounds.csv}"

JS_DIRS=(
"$SCRIPT_DIR/../queries/Relational_Equivalent_Queries"
)

MAX_EXECUTION_TIME=18000

ARANGOSH=(
  arangosh
  --server.endpoint "${ARANGODB_SHELL_ENDPOINT:-tcp://127.0.0.1:8529}"
  --server.database "$DB_NAME"
  --server.username "${ARANGODB_USERNAME:-root}"
  --server.request-timeout 18000
  --quiet
)
if [[ -n "${ARANGODB_PASSWORD:-}" ]]; then
  ARANGOSH+=(--server.password "$ARANGODB_PASSWORD")
fi

TMP_DIR="/tmp/arangodb_test_$(date +%s%N)"
mkdir -p "$TMP_DIR" || { echo "❌ Failed to create TMP_DIR"; exit 1; }
mkdir -p "$(dirname "$RESULT_FILE")"

############################################
# CLEANUP
############################################

cleanup() {
  pkill -P $$ 2>/dev/null || true
  rm -rf "$TMP_DIR"
  echo "🧹 Cleaned temporary files"
}
trap cleanup EXIT

############################################
# TIME CALC
############################################

calc_elapsed() {
  echo "$1 $2" | awk '{printf "%.6f",$2-$1}'
}

############################################
# MONITOR CPU & MEMORY
############################################

monitor_process() {
  local LOGFILE=$1
  local PARENT_PID=$2

  : > "$LOGFILE"

  while true; do
    if ! ps -p "$PARENT_PID" > /dev/null 2>&1; then
      break
    fi

    ps -eo %cpu,rss,args \
    | awk '/arangod/ {cpu+=$1;mem+=$2}
    END{print cpu","mem/1024}' \
    >> "$LOGFILE" 2>/dev/null

    sleep 0.05
  done
}

calc_stats() {
  local LOGFILE=$1

  awk -F',' '
  $1 ~ /^[0-9]+([.][0-9]+)?$/ && $2 ~ /^[0-9]+([.][0-9]+)?$/ {
    cpu_sum+=$1
    mem_sum+=$2

    if($1>cpu_peak) cpu_peak=$1
    if($2>mem_peak) mem_peak=$2

    count++
  }
  END{
    if(count==0) {
      print "# # # # 0"
      exit
    }

    printf "%.2f %.2f %.2f %.2f %d",
    cpu_peak,
    cpu_sum/count,
    mem_peak,
    mem_sum/count,
    count
  }
  ' "$LOGFILE"
}

csv_quote() {
  local value=${1//$'\r'/ }
  value=${value//$'\n'/ }
  value=${value//\"/\"\"}
  printf '"%s"' "$value"
}

############################################
# RUN JS QUERY
############################################

run_js() {
  local FILE=$1
  local ROUND=$2
  local QUERY_INDEX=$3

  local MON_LOG="$TMP_DIR/monitor_${QUERY_INDEX}_r${ROUND}.csv"
  local OUT_LOG="$TMP_DIR/query_${QUERY_INDEX}_r${ROUND}.out"
  : > "$MON_LOG"
  : > "$OUT_LOG"

  JS_TIME="#"
  JS_CPU_PEAK="#"
  JS_CPU_AVG="#"
  JS_MEM_PEAK="#"
  JS_MEM_AVG="#"
  JS_SAMPLE_COUNT=0
  JS_RESULT_TEXT=""
  JS_STATUS="FAILED"

  monitor_process "$MON_LOG" $$ &
  local MON_PID=$!

  local START=$(date +%s.%N)

  timeout $MAX_EXECUTION_TIME \
    "${ARANGOSH[@]}" --javascript.execute "$FILE" \
    > "$OUT_LOG" 2>&1

  local EXIT_CODE=$?

  local END=$(date +%s.%N)
  local COST=$(calc_elapsed "$START" "$END")
  JS_TIME="$COST"

  kill $MON_PID 2>/dev/null || true
  wait $MON_PID 2>/dev/null || true

  if [ $EXIT_CODE -eq 124 ]; then
    JS_STATUS="TIMEOUT"
    JS_RESULT_TEXT="timeout after ${MAX_EXECUTION_TIME}s"
    echo "❌ TIMEOUT: $FILE"
  elif [ $EXIT_CODE -ne 0 ]; then
    JS_STATUS="FAILED"
    JS_RESULT_TEXT=$(tail -n 1 "$OUT_LOG" 2>/dev/null)
    echo "❌ FAILED: $FILE"
    cat "$OUT_LOG"
  else
    local stats=$(calc_stats "$MON_LOG")
    read -r JS_CPU_PEAK JS_CPU_AVG JS_MEM_PEAK JS_MEM_AVG JS_SAMPLE_COUNT <<< "$stats"

    JS_RESULT_TEXT=$(tail -n 1 "$OUT_LOG" 2>/dev/null)
    JS_STATUS="OK"

    echo "✅ DONE: $FILE (time: $COST sec, samples: $JS_SAMPLE_COUNT)"
  fi
}

############################################
# MEDIAN
############################################

median() {
  printf "%s\n" "$@" | sort -n | awk '{a[NR]=$1} END {print a[int((NR+1)/2)]}'
}

############################################
# INIT
############################################

echo "file,time_sec,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,result,status" > "$RESULT_FILE"

echo "🔍 Testing ArangoDB connection..."
if ! "${ARANGOSH[@]}" --javascript.execute-string "db._collections();" > /dev/null 2>&1; then
  echo "❌ ArangoDB connection failed"
  exit 1
fi
echo "✅ ArangoDB connection OK"

echo "🚀 Starting benchmark (3 global rounds)..."

############################################
# COLLECT FILE LIST FIRST
############################################

FILES=()
for DIR in "${JS_DIRS[@]}"; do
  while IFS= read -r -d '' FILE; do
    FILES+=("$FILE")
  done < <(find "$DIR" -type f -name "*.js" -print0 | sort -z -V)
done

############################################
# STORAGE FOR EACH FILE
############################################

declare -A RUN_TIME
declare -A RUN_CPU_PEAK
declare -A RUN_CPU_AVG
declare -A RUN_MEM_PEAK
declare -A RUN_MEM_AVG
declare -A RUN_SAMPLE_COUNT
declare -A RUN_RESULT
declare -A RUN_STATUS

############################################
# OUTER ROUND LOOP (关键修改点)
############################################

QUERY_INDEX=0
for ROUND in 1 2 3; do
  echo "=============================="
  echo "🔥 ROUND $ROUND START"
  echo "=============================="

  for FILE in "${FILES[@]}"; do
    QUERY_INDEX=$((QUERY_INDEX + 1))
    echo "📋 Running: $FILE"

    run_js "$FILE" "$ROUND" "$QUERY_INDEX"

    # Store one structured record per file and round; metrics stay correlated.
    RECORD_KEY="${FILE}|${ROUND}"
    RUN_TIME["$RECORD_KEY"]="$JS_TIME"
    RUN_CPU_PEAK["$RECORD_KEY"]="$JS_CPU_PEAK"
    RUN_CPU_AVG["$RECORD_KEY"]="$JS_CPU_AVG"
    RUN_MEM_PEAK["$RECORD_KEY"]="$JS_MEM_PEAK"
    RUN_MEM_AVG["$RECORD_KEY"]="$JS_MEM_AVG"
    RUN_SAMPLE_COUNT["$RECORD_KEY"]="$JS_SAMPLE_COUNT"
    RUN_RESULT["$RECORD_KEY"]="$JS_RESULT_TEXT"
    RUN_STATUS["$RECORD_KEY"]="$JS_STATUS"
  done

done

############################################
# FINAL AGGREGATION (median)
############################################

echo "📊 Aggregating results..."

for FILE in "${FILES[@]}"; do
  OK_ROUNDS=()
  ALL_ROUNDS=(1 2 3)
  for ROUND in "${ALL_ROUNDS[@]}"; do
    RECORD_KEY="${FILE}|${ROUND}"
    if [[ "${RUN_STATUS[$RECORD_KEY]}" == "OK" ]]; then
      OK_ROUNDS+=("$ROUND")
    fi
  done

  if ((${#OK_ROUNDS[@]} > 0)); then
    TIMES=()
    for ROUND in "${OK_ROUNDS[@]}"; do
      RECORD_KEY="${FILE}|${ROUND}"
      TIMES+=("${RUN_TIME[$RECORD_KEY]}")
    done
    TIME_MED=$(median "${TIMES[@]}")

    SELECTED_ROUND="${OK_ROUNDS[0]}"
    for ROUND in "${OK_ROUNDS[@]}"; do
      RECORD_KEY="${FILE}|${ROUND}"
      if [[ "${RUN_TIME[$RECORD_KEY]}" == "$TIME_MED" ]]; then
        SELECTED_ROUND="$ROUND"
        break
      fi
    done

    RECORD_KEY="${FILE}|${SELECTED_ROUND}"
    STATUS="OK"
    if ((${#OK_ROUNDS[@]} < 3)); then
      STATUS="PARTIAL_OK"
    fi
    printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$(csv_quote "$FILE")" \
      "${RUN_TIME[$RECORD_KEY]}" \
      "${RUN_CPU_PEAK[$RECORD_KEY]}" \
      "${RUN_CPU_AVG[$RECORD_KEY]}" \
      "${RUN_MEM_PEAK[$RECORD_KEY]}" \
      "${RUN_MEM_AVG[$RECORD_KEY]}" \
      "$(csv_quote "${RUN_RESULT[$RECORD_KEY]}")" \
      "$(csv_quote "$STATUS")" >> "$RESULT_FILE"
  else
    RECORD_KEY="${FILE}|1"
    STATUS="FAILED"
    if [[ "${RUN_STATUS[$RECORD_KEY]}" == "TIMEOUT" ]]; then
      STATUS="TIMEOUT"
    fi
    printf '%s,%s,#,#,#,#,%s,%s\n' \
      "$(csv_quote "$FILE")" \
      "${RUN_TIME[$RECORD_KEY]}" \
      "$(csv_quote "${RUN_RESULT[$RECORD_KEY]}")" \
      "$(csv_quote "$STATUS")" >> "$RESULT_FILE"
  fi

done

echo -e "\n🎉 Benchmark finished!"
echo "📊 Results saved to: $RESULT_FILE"
