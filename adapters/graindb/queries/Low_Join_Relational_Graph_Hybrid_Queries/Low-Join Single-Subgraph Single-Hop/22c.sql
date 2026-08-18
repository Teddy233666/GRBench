SELECT
    MIN(t.paperid) AS cited_paperid,
    MIN(ln.laureate_id) AS minNobel
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p:Papers)-[pr:Link_NIH]->(n:NIH_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
    AND p.citation_count = 1
) t

LEFT JOIN link_nobellaureates ln
  ON t.paperid = ln.paperid;