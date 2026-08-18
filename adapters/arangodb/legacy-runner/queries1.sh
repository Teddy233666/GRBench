#!/usr/bin/env bash

############################################
# CONFIG
############################################

DB_NAME="_system"

RESULT_FILE="legacy_core/test/arangodb/execution_times1_join.csv"

JS_DIRS=(
"legacy_core/tasks/arangodb_task/agensgraph_task/Pure_Join_Queries"
)

MAX_EXECUTION_TIME=18000

ARANGOSH="arangosh \
  --server.endpoint tcp://127.0.0.1:8529 \
  --server.authentication false \
  --server.database $DB_NAME \
   --server.request-timeout 18000 \
  --quiet"

TMP_DIR="/tmp/arangodb_test_$(date +%s%N)"
mkdir -p "$TMP_DIR" || { echo "❌ Failed to create TMP_DIR"; exit 1; }

TMP_OUT="$TMP_DIR/out.log"

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

  touch "$LOGFILE"

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
  {
    cpu_sum+=$1
    mem_sum+=$2

    if($1>cpu_peak) cpu_peak=$1
    if($2>mem_peak) mem_peak=$2

    count++
  }
  END{
    if(count==0) count=1

    printf "%.2f %.2f %.2f %.2f",
    cpu_peak,
    cpu_sum/count,
    mem_peak,
    mem_sum/count
  }
  ' "$LOGFILE"
}

############################################
# RUN JS QUERY
############################################

run_js() {
  local FILE=$1
  local result="#,#,#,#,#,\"#\""
  local status="TIMEOUT"

  local MON_LOG="$TMP_DIR/monitor.log"

  monitor_process "$MON_LOG" $$ &
  local MON_PID=$!

  local START=$(date +%s.%N)

  timeout $MAX_EXECUTION_TIME \
    $ARANGOSH --javascript.execute "$FILE" \
    > "$TMP_OUT" 2>&1

  local EXIT_CODE=$?

  local END=$(date +%s.%N)
  local COST=$(calc_elapsed "$START" "$END")

  kill $MON_PID 2>/dev/null || true
  wait $MON_PID 2>/dev/null || true

  if [ $EXIT_CODE -eq 124 ]; then
    echo "❌ TIMEOUT: $FILE"
  elif [ $EXIT_CODE -ne 0 ]; then
    echo "❌ FAILED: $FILE"
    cat "$TMP_OUT"
  else
    local stats=$(calc_stats "$MON_LOG")
    read cpu_peak cpu_avg mem_peak mem_avg <<< "$stats"

    local query_result=$(tail -n 1 "$TMP_OUT")
    query_result=$(echo "$query_result" | sed 's/"/'\''/g')

    result="$COST,$cpu_peak,$cpu_avg,$mem_peak,$mem_avg,\"$query_result\""
    status="OK"

    echo "✅ DONE: $FILE (time: $COST sec)"
  fi

  JS_RESULT="$result"
  JS_STATUS="$status"
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
if ! $ARANGOSH --javascript.execute-string "db._collections();" > /dev/null 2>&1; then
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

declare -A TIME_LIST
declare -A CPU_PEAK_LIST
declare -A CPU_AVG_LIST
declare -A MEM_PEAK_LIST
declare -A MEM_AVG_LIST
declare -A RESULT_LIST

############################################
# OUTER ROUND LOOP (关键修改点)
############################################

for ROUND in 1 2 3; do
  echo "=============================="
  echo "🔥 ROUND $ROUND START"
  echo "=============================="

  for FILE in "${FILES[@]}"; do
    echo "📋 Running: $FILE"

    run_js "$FILE"

    # append per file per round
    TIME_LIST["$FILE"]+="$JS_RESULT|"
    CPU_PEAK_LIST["$FILE"]+="$JS_RESULT|"
    CPU_AVG_LIST["$FILE"]+="$JS_RESULT|"
    MEM_PEAK_LIST["$FILE"]+="$JS_RESULT|"
    MEM_AVG_LIST["$FILE"]+="$JS_RESULT|"
    RESULT_LIST["$FILE"]+="$JS_RESULT|"
  done

done

############################################
# FINAL AGGREGATION (median)
############################################

echo "📊 Aggregating results..."

for FILE in "${FILES[@]}"; do

  # 拆 3 轮结果
  IFS='|' read -r t1 t2 t3 <<< "${TIME_LIST[$FILE]}"

  # 这里只简单解析 time（你也可以扩展 CPU/MEM）
  TIMES=($t1 $t2 $t3)

  TIME_MED=$(median "${TIMES[@]}")

  # 直接写（简化版：保留你原结构）
  echo "\"$FILE\",$TIME_MED,#,#,#,#,#,OK" >> "$RESULT_FILE"

done

echo -e "\n🎉 Benchmark finished!"
echo "📊 Results saved to: $RESULT_FILE"