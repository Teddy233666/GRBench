#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${GRAINDB_DATABASE:-.local/graindb/graindb_3.db}"
DB_CLI="./duckdb_cli"

RESULT_FILE="legacy_core/test/graindb/update1.csv"

SQL_DIRS=(
)


TMP_DIR="/tmp/duck_monitor_$$"
mkdir -p "$TMP_DIR"

echo "🚀 Starting DuckDB..."

coproc DB { $DB_CLI "$DB_PATH"; }

DB_IN=${DB[1]}
DB_OUT=${DB[0]}
monitor_process() {
  LOGFILE=$1

  : > "$LOGFILE"

  CGROUP_V1="/sys/fs/cgroup/memory/memory.usage_in_bytes"
  CGROUP_V2="/sys/fs/cgroup/memory.current"

  while true; do

    # CPU（保持你原来的 ps 逻辑，不动）
    cpu=$(ps -eo %cpu,args | awk '/duckdb/ {sum+=$1} END {print sum+0}')

    # ==============================
    # MEM：统一 PostgreSQL 方式（cgroup）
    # ==============================
    if [[ -f "$CGROUP_V1" ]]; then
      mem_bytes=$(cat "$CGROUP_V1")
    elif [[ -f "$CGROUP_V2" ]]; then
      mem_bytes=$(cat "$CGROUP_V2")
    else
      mem_bytes=0
    fi

    mem_mb=$(awk -v b="$mem_bytes" 'BEGIN{printf "%.2f", b/1024/1024}')

    # 输出格式统一（cpu,mem）
    echo "$cpu,$mem_mb" >> "$LOGFILE"

    sleep 1
  done
}

calc_stats() {
  LOGFILE=$1

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
  }' "$LOGFILE"
}

############################################
# 初始化图
############################################
echo "🚀 Initializing Graph Schema..."

cat <<EOF >&"$DB_IN"
SELECT 'INIT_DONE';
EOF

while read -r line <&"$DB_OUT"; do
  [[ "$line" == *"INIT_DONE"* ]] && break
done

echo "✅ Graph initialized"

############################################
# CSV
############################################
echo "sql_file,time_sec,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,status" > "$RESULT_FILE"

############################################
# SQL 执行
############################################
run_sql_once() {
  local sql="$1"
  local logfile="$2"

  local tag="END_$(date +%s%N)"

  monitor_process "$logfile" &
  local MON_PID=$!

  local START=$(date +%s.%N)

  sql=$(echo "$sql" | sed 's/;[[:space:]]*$//')
  echo "$sql;" >&"$DB_IN"
  echo "SELECT '$tag';" >&"$DB_IN"

  local HAS_ERROR=0

  while read -r line <&"$DB_OUT"; do
    if [[ "$line" == *"Error"* ]] || [[ "$line" == *"Exception"* ]]; then
      HAS_ERROR=1
    fi
    [[ "$line" == *"$tag"* ]] && break
  done

  local END=$(date +%s.%N)
  kill "$MON_PID" 2>/dev/null || true

  local COST=$(echo "$START $END" | awk '{printf "%.6f",$2-$1}')

  read -r cpu_peak cpu_avg mem_peak mem_avg <<< "$(calc_stats "$logfile")"

  if [[ "$HAS_ERROR" -eq 1 ]]; then
    echo "FAILED"
  else
    echo "$COST $cpu_peak $cpu_avg $mem_peak $mem_avg"
  fi
}

############################################
# 主循环（每个 SQL 只跑 1 次）
############################################
for DIR in "${SQL_DIRS[@]}"; do
  mapfile -t FILES < <(find "$DIR" -type f -name "*.sql" | sort -V)

  for FILE in "${FILES[@]}"; do
    SQL=$(sed '/^\s*$/d' "$FILE")
    LOGFILE="$TMP_DIR/$(basename "$FILE").log"

    RESULT=$(run_sql_once "$SQL" "$LOGFILE")

    if [[ "$RESULT" == FAILED* ]]; then
      STATUS="FAILED"
      echo "\"$FILE\",,,,,$STATUS" >> "$RESULT_FILE"
      echo "❌ $FILE → status=$STATUS"
    else
      read -r t cpk cav mpk mav <<< "$RESULT"
      STATUS="OK"
      echo "\"$FILE\",$t,$cpk,$cav,$mpk,$mav,$STATUS" >> "$RESULT_FILE"
      echo "✅ $FILE → time=$t cpu=$cpk mem=$mpk status=$STATUS"
    fi
  done
done

############################################
# 关闭
############################################
echo "🛑 Closing DuckDB..."
exec {DB_IN}>&-
exec {DB_OUT}>&-

echo "🎉 Finished → $RESULT_FILE"
