#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${GRAINDB_DATABASE:-.local/graindb/graindb_2.db}"
DB_CLI="./duckdb_cli"

RESULT_FILE="legacy_core/test/graindb/sql_execution_times_2.csv"

SQL_DIRS=(
"legacy_core/tasks/graindb_task_copy/High_Join_Relational_Graph_Hybrid_Queries/High-Join Multi-Subgraph Multi-Hop"
)

TMP_DIR="/tmp/duck_monitor_$$"
mkdir -p "$TMP_DIR"

echo "🚀 Starting DuckDB..."

coproc DB { $DB_CLI "$DB_PATH"; }

DB_IN=${DB[1]}
DB_OUT=${DB[0]}

############################################
# CPU / MEM monitor
############################################
monitor_process() {
  LOGFILE=$1
  : > "$LOGFILE"

  CGROUP_V1="/sys/fs/cgroup/memory/memory.usage_in_bytes"
  CGROUP_V2="/sys/fs/cgroup/memory.current"

  while true; do
    cpu=$(ps -eo %cpu,args | awk '/duckdb/ {sum+=$1} END {print sum+0}')

    if [[ -f "$CGROUP_V1" ]]; then
      mem_bytes=$(cat "$CGROUP_V1")
    else
      mem_bytes=$(cat "$CGROUP_V2" 2>/dev/null || echo 0)
    fi

    mem_mb=$(awk -v b="$mem_bytes" 'BEGIN{printf "%.2f", b/1024/1024}')

    echo "$cpu,$mem_mb" >> "$LOGFILE"
    sleep 2
  done
}

############################################
# 单次 SQL 执行
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

  cpu_peak=$(awk -F',' 'max<$1{max=$1} END{print max+0}' "$logfile")
  mem_peak=$(awk -F',' 'max<$2{max=$2} END{print max+0}' "$logfile")

  cpu_avg=$(awk -F',' '{s+=$1} END{printf "%.6f", s/NR}' "$logfile")
  mem_avg=$(awk -F',' '{s+=$2} END{printf "%.6f", s/NR}' "$logfile")

  if [[ "$HAS_ERROR" -eq 1 ]]; then
    echo "FAILED"
  else
    echo "$COST $cpu_peak $cpu_avg $mem_peak $mem_avg"
  fi
}

############################################
# median
############################################
median_of_three() {
  printf "%s\n" "$@" | sort -n | awk 'NR==2'
}

############################################
# 初始化 Graph
############################################
echo "🚀 Initializing Graph Schema..."

cat <<EOF >&"$DB_IN"
CREATE VERTEX Papers ON Papers;
CREATE VERTEX Authors_Gender ON Authors_Gender;
CREATE VERTEX Affiliations ON Affiliations;
CREATE VERTEX Fields ON Fields;
CREATE VERTEX NSF_Metadata ON NSF_Metadata;
CREATE VERTEX NIH_Metadata ON NIH_Metadata;
CREATE VERTEX clinicaltrials_metadata ON clinicaltrials_metadata;
CREATE VERTEX Newsfeed_Metadata ON Newsfeed_Metadata;
CREATE VERTEX Twitter_Metadata ON Twitter_Metadata;

CREATE EDGE Papers_to_Authors ON Papers_to_Authors ( FROM Papers REFERENCES paperid, TO Authors_Gender REFERENCES authorid );
CREATE EDGE contributed_from ON contributed_from ( FROM Papers REFERENCES paperid, TO Affiliations REFERENCES institutionid );
CREATE EDGE affiliated_with ON affiliated_with ( FROM Authors_Gender REFERENCES authorid, TO Affiliations REFERENCES institutionid );
CREATE EDGE affl_assoc_affl ON affl_assoc_affl ( FROM Affiliations REFERENCES institution_id, TO Affiliations REFERENCES associated_institution_id );
CREATE EDGE PaperReferences ON PaperReferences ( FROM Papers REFERENCES citing_paperid, TO Papers REFERENCES cited_paperid );
CREATE EDGE Link_NSF ON Link_NSF ( FROM Papers REFERENCES paperid, TO NSF_Metadata REFERENCES award_id );
CREATE EDGE Link_NIH ON Link_NIH ( FROM Papers REFERENCES paperid, TO NIH_Metadata REFERENCES award_id );
CREATE EDGE Link_ClinicalTrials ON Link_ClinicalTrials ( FROM Papers REFERENCES paperid, TO clinicaltrials_metadata REFERENCES nct_id );
CREATE EDGE link_newsfeed ON link_newsfeed ( FROM Papers REFERENCES paperid, TO Newsfeed_Metadata REFERENCES newsfeed_id );
CREATE EDGE link_twitter ON link_twitter ( FROM Papers REFERENCES paperid, TO Twitter_Metadata REFERENCES tweet_id );
CREATE EDGE PaperFields ON PaperFields ( FROM Papers REFERENCES paperid, TO Fields REFERENCES fieldid );
SELECT 'INIT_DONE';
EOF

while read -r line <&"$DB_OUT"; do
  [[ "$line" == *"INIT_DONE"* ]] && break
done

echo "✅ Graph initialized"

############################################
# CSV header
############################################
echo "sql_file,median_time_sec,cpu_peak,cpu_avg,mem_peak_mb,mem_avg_mb,status" > "$RESULT_FILE"

############################################
# GLOBAL ROUNDS EXECUTION
############################################

mapfile -t FILES < <(find "${SQL_DIRS[@]}" -type f -name "*.sql" | sort -V)

declare -A TIMES CPU_PEAKS CPU_AVGS MEM_PEAKS MEM_AVGS STATUSS

for FILE in "${FILES[@]}"; do
  TIMES["$FILE"]=""
  CPU_PEAKS["$FILE"]=""
  CPU_AVGS["$FILE"]=""
  MEM_PEAKS["$FILE"]=""
  MEM_AVGS["$FILE"]=""
  STATUSS["$FILE"]="OK"
done

for ROUND in {1..3}; do
  echo "🚀 Global Round $ROUND"

  for FILE in "${FILES[@]}"; do
    SQL=$(sed '/^\s*$/d' "$FILE")
    LOGFILE="$TMP_DIR/$(basename "$FILE")_r${ROUND}.log"

    RESULT=$(run_sql_once "$SQL" "$LOGFILE")

    if [[ "$RESULT" == FAILED* ]]; then
      STATUSS["$FILE"]="FAILED"
      continue
    fi

    read t cpk cav mpk mav <<< "$RESULT"

    TIMES["$FILE"]+="$t "
    CPU_PEAKS["$FILE"]+="$cpk "
    CPU_AVGS["$FILE"]+="$cav "
    MEM_PEAKS["$FILE"]+="$mpk "
    MEM_AVGS["$FILE"]+="$mav "
  done
done

############################################
# FINAL AGGREGATION
############################################
for FILE in "${FILES[@]}"; do

  if [[ "${STATUSS[$FILE]}" == "FAILED" ]]; then
    echo "\"$FILE\",0,0,0,0,0,FAILED" >> "$RESULT_FILE"
    continue
  fi

  read -ra TARR <<< "${TIMES[$FILE]}"
  read -ra CPARR <<< "${CPU_PEAKS[$FILE]}"
  read -ra CAARR <<< "${CPU_AVGS[$FILE]}"
  read -ra MPARR <<< "${MEM_PEAKS[$FILE]}"
  read -ra MAARR <<< "${MEM_AVGS[$FILE]}"

  MEDIAN=$(printf "%s\n" "${TARR[@]}" | sort -n | awk 'NR==2')

  CPU_PEAK=$(printf "%s\n" "${CPARR[@]}" | sort -n | tail -1)
  MEM_PEAK=$(printf "%s\n" "${MPARR[@]}" | sort -n | tail -1)

  CPU_AVG=$(printf "%s\n" "${CAARR[@]}" | awk '{s+=$1} END{printf "%.6f", s/NR}')
  MEM_AVG=$(printf "%s\n" "${MAARR[@]}" | awk '{s+=$1} END{printf "%.6f", s/NR}')

  echo "\"$FILE\",$MEDIAN,$CPU_PEAK,$CPU_AVG,$MEM_PEAK,$MEM_AVG,OK" >> "$RESULT_FILE"

  echo "✅ $FILE → time=$MEDIAN cpu=$CPU_PEAK mem=$MEM_PEAK"
done

############################################
# cleanup
############################################
echo "🛑 Closing DuckDB..."
exec {DB_IN}>&-
exec {DB_OUT}>&-

echo "🎉 Finished → $RESULT_FILE"
