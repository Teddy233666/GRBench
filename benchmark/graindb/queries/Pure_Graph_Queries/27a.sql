SELECT
    MIN(t.paperid),
    MIN(t2.award_id)
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p:Papers)-[pr:Link_NIH]->(n:NIH_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 3
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.award_id
  FROM (p:Papers)-[pr:Link_NSF]->(n:NSF_Metadata)
) t2
ON t.paperid = t2.paperid;