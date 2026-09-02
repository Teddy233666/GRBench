SELECT
    MIN(t.paperid) AS cited_paperid,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(h0.paperid) AS minh0paperid
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p IS Papers)-[pr IS  Link_NSF]->(n IS NSF_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 1
) t

LEFT JOIN papersources ps
  ON t.paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON t.paperid = ln.paperid

LEFT JOIN hit_papers_level0 h0
  ON t.paperid = h0.paperid;