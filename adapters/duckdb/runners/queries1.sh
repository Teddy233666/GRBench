#!/usr/bin/env bash
set -euo pipefail

DB_FILE="${GRBENCH_DUCKDB_DB:-.local/duckdb/sciscinet_graph_2.duckdb}"
EXEC_TIME_LOG="${GRBENCH_DUCKDB_RESULT:-.local/results/duckdb_update.csv}"

SQL_DIRS=(
  "adapters/duckdb/queries/Update"
)

TMP_DIR="/tmp/duck_monitor_$$"
mkdir -p "$TMP_DIR"
mkdir -p "$(dirname "$EXEC_TIME_LOG")"

echo "sql_file_path,median_execution_time_seconds,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,status,result" > "$EXEC_TIME_LOG"

############################################
# CPU / MEM monitor
############################################
monitor_process() {
  LOGFILE=$1
  while true; do
    ps -eo %cpu,rss,args \
    | awk '/duckdb/ {cpu+=$1;mem+=$2}
           END{print cpu","mem/1024}' \
    >> "$LOGFILE"
    sleep 0.05
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
    printf "%.2f %.2f %.2f %.2f", cpu_peak, cpu_sum/count, mem_peak, mem_sum/count
  }' "$LOGFILE"
}

############################################
# DuckDB session
############################################
coproc DUCKDB_PROC {
  duckdb "$DB_FILE" 2>&1
}

exec 3>&"${DUCKDB_PROC[1]}"
exec 4<&"${DUCKDB_PROC[0]}"

cat <<EOF >&3
INSTALL duckpgq FROM community;
LOAD duckpgq;
EOF

############################################
# collect SQL files
############################################
SQL_FILES=()

for DIR in "${SQL_DIRS[@]}"; do
  while IFS= read -r -d '' SQL_FILE; do
    SQL_FILES+=("$SQL_FILE")
  done < <(find "$DIR" -type f -name "*.sql" -print0 | sort -z)
done

############################################
# execution (single pass per SQL file)
############################################
for SQL_FILE in "${SQL_FILES[@]}"; do

  echo "▶ $SQL_FILE"

  SQL_CONTENT="$(<"$SQL_FILE")"
  MARKER="DONE_$(date +%s%N)_$RANDOM"

  MON_LOG="$TMP_DIR/$(basename "$SQL_FILE").log"

  START=$(date +%s.%N)

  monitor_process "$MON_LOG" &
  MON_PID=$!

  printf "%s\n" "$SQL_CONTENT" >&3
  printf "SELECT '%s';\n" "$MARKER" >&3

  RUN_STATUS="OK"
  RESULT_BUFFER=""

  while IFS= read -r LINE <&4; do

    [[ "$LINE" == *"Error"* || "$LINE" == *"ERROR"* ]] && RUN_STATUS="FAILED"

    [[ "$LINE" == *"$MARKER"* ]] && break

    RESULT_BUFFER+="$LINE"$'\n'

  done

  END=$(date +%s.%N)
  kill "$MON_PID" 2>/dev/null || true

  ELAPSED=$(awk -v s="$START" -v e="$END" 'BEGIN{print e-s}')

  read cpu_peak cpu_avg mem_peak mem_avg <<< "$(calc_stats "$MON_LOG")"

  RESULT_CLEAN="${RESULT_BUFFER//$'\n'/ }"

  echo "\"$SQL_FILE\",$ELAPSED,$cpu_peak,$cpu_avg,$mem_peak,$mem_avg,$RUN_STATUS,\"$RESULT_CLEAN\"" >> "$EXEC_TIME_LOG"

  echo "  time=$ELAPSED"

done

############################################
# cleanup
############################################
printf ".quit\n" >&3

echo "DONE → $EXEC_TIME_LOG"
