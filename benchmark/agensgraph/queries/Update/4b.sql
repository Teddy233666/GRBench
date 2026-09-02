LOAD FROM grbench_update4_authors_gender AS a
MERGE (n:Authors_Gender {authorid: a.authorid})
SET n = to_jsonb(row_to_json(a));