#!/usr/bin/env bash

############################################
# CONFIG
############################################

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DB_USER="${AGENSGRAPH_USERNAME:-agens}"
DB_NAME="${AGENSGRAPH_DATABASE:-grbench}"
GRAPH_NAME="sciscinet_graph"

RESULT_FILE="${GRBENCH_AGENSGRAPH_RESULT:-.local/results/agensgraph/update_subset.csv}"

SQL_DIRS=(
"$SCRIPT_DIR/../queries/Update/U5a.sql"
"$SCRIPT_DIR/../queries/Update/U4b.sql"
"$SCRIPT_DIR/../queries/Update/U4a.sql"
"$SCRIPT_DIR/../queries/Update/U6b.sql"
"$SCRIPT_DIR/../queries/Update/U6a.sql"
)

############################################
# START COPROC (HOT SESSION)
############################################

coproc AGENS_PROC {
  agens -X -q -A -P pager=off -U "$DB_USER" -d "$DB_NAME"
}

AGENS_IN=${AGENS_PROC[1]}
AGENS_OUT=${AGENS_PROC[0]}

############################################
# INIT SESSION
############################################

{
echo "SET graph_path = sciscinet_graph;"
echo "\set ON_ERROR_STOP off"
} >&"$AGENS_IN"

############################################
# UTIL
############################################

calc_elapsed() {
  awk -v s="$1" -v e="$2" 'BEGIN{printf "%.6f",e-s}'
}

############################################
# RUN SQL
############################################

run_sql() {

  local FILE="$1"

  local SQL_CONTENT
  SQL_CONTENT=$(cat "$FILE")

  local START END COST
  local TMP_RESULT=""
  local ERROR=""

  START=$(date +%s.%N)

  ########################################
  # SEND SQL
  ########################################

  {
    echo "$SQL_CONTENT"
    echo "\echo __END__"
  } >&"$AGENS_IN"

  ########################################
  # READ OUTPUT
  ########################################

  local LINE

  while IFS= read -r LINE <&"$AGENS_OUT"; do

    if [[ "$LINE" == "__END__" ]]; then
      break
    fi

    TMP_RESULT+="$LINE"$'\n'

    if [[ "$LINE" =~ ^ERROR: || "$LINE" =~ ^FATAL: ]]; then
      ERROR+="$LINE "
    fi

  done

  END=$(date +%s.%N)

  COST=$(calc_elapsed "$START" "$END")

  TMP_RESULT=$(echo "$TMP_RESULT" | tr '\n' ' ' | sed 's/"/""/g')

  if [[ -n "$ERROR" ]]; then
    SQL_STATUS="FAILED"
    SQL_ERROR="$ERROR"
  else
    SQL_STATUS="OK"
    SQL_ERROR=""
  fi

  SQL_RESULT="$COST"
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
# RUN ONCE (single pass per SQL file)
############################################

mkdir -p "$(dirname "$RESULT_FILE")"
echo "sql_file,time_sec,status,result,error" > "$RESULT_FILE"

for FILE in "${SQL_FILES[@]}"; do

  echo "▶ $FILE"

  run_sql "$FILE"

  echo "\"$FILE\",$SQL_RESULT,$SQL_STATUS,\"$SQL_OUTPUT\",\"$SQL_ERROR\"" >> "$RESULT_FILE"

done

echo "📊 Results written to $RESULT_FILE"

############################################
# CLOSE SESSION
############################################

echo "\q" >&"$AGENS_IN"

echo "🎉 Benchmark finished!"
