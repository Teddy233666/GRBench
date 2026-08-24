LOAD FROM grbench_update3_papers AS p
MERGE (n:Papers {paperid: p.paperid})
SET n = to_jsonb(row_to_json(p));
