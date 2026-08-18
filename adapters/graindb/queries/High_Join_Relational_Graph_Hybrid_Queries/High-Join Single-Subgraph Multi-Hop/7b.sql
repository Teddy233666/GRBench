SELECT
    MIN(t.cited_paperid) AS cited_paperid,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
  SELECT DISTINCT
      orig.paperid AS orig_paperid,
      cited.paperid AS cited_paperid,
      cited.citation_count
  FROM (orig:Papers)-[r1:PaperReferences*3..3]->(cited:Papers)
  WHERE orig.paperid = 'W2122344208'
    AND cited.citation_count < 80
) t

LEFT JOIN papersources ps
  ON t.cited_paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON t.orig_paperid = ln.paperid

LEFT JOIN link_patents lp
  ON t.orig_paperid = lp.paperid;