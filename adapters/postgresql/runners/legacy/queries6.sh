#!/usr/bin/env bash

############################################
# CONFIG
############################################

DB_USER="postgres"
DB_NAME="postgres"

RESULT_FILE="legacy_core/test/postgresql/update1.csv"

SQL_DIRS=(
"legacy_core/tasks/postgresql_task/update/Update copy/2b.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/2a.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/3c.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/3a.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/5b.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/5a.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/6b.sql"
"legacy_core/tasks/postgresql_task/update/Update copy/6a.sql"
)

# ✅ 只跑 1 轮
RUNS=1

# ✅ 超时：18000秒 = 5小时（单位 ms）
STATEMENT_TIMEOUT_MS=18000000

############################################
# START COPROC
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

############################################
# MONITOR PROCESS  =>  已替换成容器内存版本
############################################

monitor_process() {
  local LOGFILE=$1
  local FLAG_FILE=$2

  : > "$LOGFILE"

  while [ -f "$FLAG_FILE" ]; do

    # CPU：保持原来逻辑
    cpu=$(ps -eo %cpu,args | awk '/postgres/ {sum+=$1} END {print sum}')

    # 内存：读取容器 cgroup 真实内存
    if [ -f /sys/fs/cgroup/memory/memory.usage_in_bytes ]; then
      mem_bytes=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
    else
      mem_bytes=$(cat /sys/fs/cgroup/memory.current 2>/dev/null || echo 0)
    fi
    mem_mb=$(awk -v b="$mem_bytes" 'BEGIN{print b/1024/1024}')

    echo "$cpu,$mem_mb" >> "$LOGFILE"

    sleep 0.05
  done
}

############################################
# CALC STATS  =>  完全匹配新监控
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
# RUN SQL（单轮 + 超时）
############################################

run_sql() {

  local FILE="$1"
  local SQL_CONTENT
  SQL_CONTENT=$(cat "$FILE")

  local START END COST
  local TMP_RESULT=""
  local ERROR=""

  local MON_LOG="/tmp/pg_mon_$$.log"
  local FLAG_FILE="/tmp/pg_flag_$$"

  touch "$FLAG_FILE"
  monitor_process "$MON_LOG" "$FLAG_FILE" &
  local MON_PID=$!

  START=$(date +%s.%N)

  ########################################
  # 发送 SQL（带超时）
  ########################################

  {
    echo "SET statement_timeout = ${STATEMENT_TIMEOUT_MS};"
    echo "$SQL_CONTENT"
    echo "SELECT '__END__';"
  } >&"$PSQL_IN"

  ########################################
  # 读取结果
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
  # 停止监控
  ########################################

  rm -f "$FLAG_FILE"
  wait $MON_PID 2>/dev/null

  ########################################
  # 统计
  ########################################

  read CPU_PEAK CPU_AVG MEM_PEAK MEM_AVG <<< $(calc_stats "$MON_LOG")

  ########################################
  # 清洗输出
  ########################################

  TMP_RESULT=$(echo "$TMP_RESULT" | tr '\n' ' ' | sed 's/"/""/g')

  ########################################
  # 状态判断
  ########################################

  if [[ "$ERROR" == *"statement timeout"* ]]; then
    SQL_STATUS="TIMEOUT"
  elif [[ -n "$ERROR" ]]; then
    SQL_STATUS="FAILED"
  else
    SQL_STATUS="OK"
  fi

  ########################################
  # 返回
  ########################################

  SQL_RESULT="$COST"
  SQL_CPU_PEAK="$CPU_PEAK"
  SQL_CPU_AVG="$CPU_AVG"
  SQL_MEM_PEAK="$MEM_PEAK"
  SQL_MEM_AVG="$MEM_AVG"
  SQL_OUTPUT="$TMP_RESULT"
  SQL_ERROR="$ERROR"
  SQL_STATUS="$SQL_STATUS"
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
# OUTPUT HEADER
############################################

echo "sql_file,time_sec,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,status,result,error" > "$RESULT_FILE"

############################################
# 单轮执行
############################################

echo "🚀 Single Run Mode"

for FILE in "${SQL_FILES[@]}"; do

  echo "▶ $FILE"

  run_sql "$FILE"

  echo "\"$FILE\",$SQL_RESULT,$SQL_CPU_PEAK,$SQL_CPU_AVG,$SQL_MEM_PEAK,$SQL_MEM_AVG,$SQL_STATUS,\"$SQL_OUTPUT\",\"$SQL_ERROR\"" >> "$RESULT_FILE"

done

############################################
# CLOSE
############################################

echo "\q" >&"$PSQL_IN"

echo "🎉 Benchmark finished!"