SELECT
    MIN(t.orig_paperid) AS cited_paperid,
    MIN(s.sourceid) AS minSource
FROM
(
  SELECT DISTINCT
      orig.paperid AS orig_paperid,
      cited.paperid AS cited_paperid,
      cited.citation_count
  FROM (orig:Papers)-[r1:PaperReferences*3..3]->(cited:Papers)
  WHERE orig.paperid = 'W2122344208'
    AND cited.citation_count < 150
) t

LEFT JOIN papersources ps
  ON t.orig_paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid;