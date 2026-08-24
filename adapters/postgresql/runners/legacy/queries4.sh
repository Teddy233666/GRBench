#!/usr/bin/env bash

############################################
# CONFIG
############################################

DB_USER="postgres"
DB_NAME="postgres"

RESULT_FILE="legacy_core/test/postgresql/time2.csv"

SQL_DIRS=(
  "legacy_core/tasks/postgresql_task/High_Join_Relational_Graph_Hybrid_Queries"
"legacy_core/tasks/postgresql_task/Low_Join_Relational_Graph_Hybrid_Queries"
"legacy_core/tasks/postgresql_task/Pure_Graph_Queries"
)

RUNS=3

# 18000 秒 = 5 小时
STATEMENT_TIMEOUT_MS=18000000

############################################
# START COPROC (HOT SESSION)
############################################

coproc PSQL_PROC {
  psql -X -q -A -P pager=off -U "$DB_USER" -d "$DB_NAME"
}

PSQL_IN=${PSQL_PROC[1]}
PSQL_OUT=${PSQL_PROC[0]}

############################################
# INIT EXTENSION
############################################

{
echo "CREATE EXTENSION IF NOT EXISTS age;"
echo "LOAD 'age';"
echo "SET search_path = ag_catalog, \"\$user\", public;"
echo "\set ON_ERROR_STOP off"
} >&"$PSQL_IN"

############################################
# UTIL
############################################

calc_elapsed() {
  awk -v s="$1" -v e="$2" 'BEGIN{printf "%.6f",e-s}'
}

median() {
  printf "%s\n" "$@" | sort -n | awk '{a[NR]=$1} END{print a[int((NR+1)/2)]}'
}

############################################
# MONITOR PROCESS (CPU 不变, 内存改为容器内存)
############################################

monitor_process() {
  local LOGFILE=$1
  local FLAG_FILE=$2

  : > "$LOGFILE"

  while [ -f "$FLAG_FILE" ]; do

    # ======================
    # CPU：完全保留你原来的逻辑
    # ======================
    cpu=$(ps -eo %cpu,args | awk '/postgres/ {sum+=$1} END {print sum}')

    # ======================
    # 内存：改为容器真实内存（cgroup）
    # ======================
    if [ -f /sys/fs/cgroup/memory/memory.usage_in_bytes ]; then
      mem_bytes=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
    else
      mem_bytes=$(cat /sys/fs/cgroup/memory.current 2>/dev/null || echo 0)
    fi
    mem_mb=$(awk -v b="$mem_bytes" 'BEGIN{print b/1024/1024}')

    # 输出：cpu,内存(MB)
    echo "$cpu,$mem_mb" >> "$LOGFILE"

    sleep 0.05
  done
}

############################################
# CALC STATS (完全不变)
############################################

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
# RUN SQL (完全不变)
############################################

run_sql() {

  local FILE="$1"
  local SQL_CONTENT
  SQL_CONTENT=$(cat "$FILE")

  local START END COST
  local TMP_RESULT=""
  local ERROR=""

  ########################################
  # START MONITOR
  ########################################

  local MON_LOG="/tmp/pg_mon_$$.log"
  local FLAG_FILE="/tmp/pg_flag_$$"

  touch "$FLAG_FILE"
  monitor_process "$MON_LOG" "$FLAG_FILE" &
  local MON_PID=$!

  START=$(date +%s.%N)

  ########################################
  # SEND SQL（关键：加超时）
  ########################################

  {
    echo "SET statement_timeout = ${STATEMENT_TIMEOUT_MS};"
    echo "$SQL_CONTENT"
    echo "SELECT '__END__';"
  } >&"$PSQL_IN"

  ########################################
  # READ OUTPUT
  ########################################

  local LINE

  while IFS= read -r LINE <&"$PSQL_OUT"; do

    if [[ "$LINE" == "__END__" ]]; then
      break
    fi

    TMP_RESULT+="$LINE"$'\n'

    if [[ "$LINE" =~ ^ERROR: ]]; then
      ERROR+="$LINE "
    fi

  done

  END=$(date +%s.%N)
  COST=$(calc_elapsed "$START" "$END")

  ########################################
  # STOP MONITOR
  ########################################

  rm -f "$FLAG_FILE"
  wait $MON_PID 2>/dev/null

  ########################################
  # CALC STATS
  ########################################

  read CPU_PEAK CPU_AVG MEM_PEAK MEM_AVG <<< $(calc_stats "$MON_LOG")

  ########################################
  # CLEAN OUTPUT
  ########################################

  TMP_RESULT=$(echo "$TMP_RESULT" | tr '\n' ' ' | sed 's/"/""/g')

  ########################################
  # STATUS
  ########################################

  if [[ "$ERROR" == *"statement timeout"* ]]; then
    SQL_STATUS="TIMEOUT"
    SQL_ERROR="$ERROR"
  elif [[ -n "$ERROR" ]]; then
    SQL_STATUS="FAILED"
    SQL_ERROR="$ERROR"
  else
    SQL_STATUS="OK"
    SQL_ERROR=""
  fi

  ########################################
  # RESULT
  ########################################

  SQL_RESULT="$COST"
  SQL_CPU_PEAK="$CPU_PEAK"
  SQL_CPU_AVG="$CPU_AVG"
  SQL_MEM_PEAK="$MEM_PEAK"
  SQL_MEM_AVG="$MEM_AVG"
  SQL_OUTPUT="$TMP_RESULT"
}

############################################
# COLLECT FILES
############################################

SQL_FILES=()

for DIR in "${SQL_DIRS[@]}"; do
  while IFS= read -r -d '' FILE; do
    SQL_FILES+=("$FILE")
  done < <(find "$DIR" -type f -name "*.sql" -print0 | sort -z -V)
done

############################################
# STORAGE
############################################

declare -A TIME_MAP
declare -A CPU_PEAK_MAP
declare -A CPU_AVG_MAP
declare -A MEM_PEAK_MAP
declare -A MEM_AVG_MAP

declare -A RESULT_MAP
declare -A STATUS_MAP
declare -A ERROR_MAP

############################################
# BENCHMARK LOOP
############################################

echo "sql_file,time_sec,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,status,result,error" > "$RESULT_FILE"

for ((run=1; run<=RUNS; run++)); do

  echo "============================"
  echo "🚀 Round $run / $RUNS"
  echo "============================"

  for FILE in "${SQL_FILES[@]}"; do

    echo "▶ $FILE"

    run_sql "$FILE"

    TIME_MAP["$FILE"]+="$SQL_RESULT "
    CPU_PEAK_MAP["$FILE"]+="$SQL_CPU_PEAK "
    CPU_AVG_MAP["$FILE"]+="$SQL_CPU_AVG "
    MEM_PEAK_MAP["$FILE"]+="$SQL_MEM_PEAK "
    MEM_AVG_MAP["$FILE"]+="$SQL_MEM_AVG "

    if [[ $run -eq $RUNS ]]; then
      RESULT_MAP["$FILE"]="$SQL_OUTPUT"
      STATUS_MAP["$FILE"]="$SQL_STATUS"
      ERROR_MAP["$FILE"]="$ERROR"
    fi

  done
done

############################################
# WRITE RESULT
############################################

echo "📊 Writing results..."

for FILE in "${SQL_FILES[@]}"; do

  read -a TIMES <<< "${TIME_MAP[$FILE]}"
  read -a CPU_P <<< "${CPU_PEAK_MAP[$FILE]}"
  read -a CPU_A <<< "${CPU_AVG_MAP[$FILE]}"
  read -a MEM_P <<< "${MEM_PEAK_MAP[$FILE]}"
  read -a MEM_A <<< "${MEM_AVG_MAP[$FILE]}"

  MED_TIME=$(median "${TIMES[@]}")
  MED_CPU_P=$(median "${CPU_P[@]}")
  MED_CPU_A=$(median "${CPU_A[@]}")
  MED_MEM_P=$(median "${MEM_P[@]}")
  MED_MEM_A=$(median "${MEM_A[@]}")

  STATUS=${STATUS_MAP["$FILE"]}
  RESULT=${RESULT_MAP["$FILE"]}
  ERROR=${ERROR_MAP["$FILE"]}

  echo "\"$FILE\",$MED_TIME,$MED_CPU_P,$MED_CPU_A,$MED_MEM_P,$MED_MEM_A,$STATUS,\"$RESULT\",\"$ERROR\"" >> "$RESULT_FILE"

done

############################################
# CLOSE SESSION
############################################

echo "\q" >&"$PSQL_IN"

echo "🎉 Benchmark finished!"