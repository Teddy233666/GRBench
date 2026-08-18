SELECT
    MIN(t.paperid) AS cited_paperid,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p:Papers)-[pr:Link_NIH]->(n:NIH_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 3
) t

LEFT JOIN papersources ps
  ON t.paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON t.paperid = ln.paperid

LEFT JOIN link_patents lp
  ON t.paperid = lp.paperid;