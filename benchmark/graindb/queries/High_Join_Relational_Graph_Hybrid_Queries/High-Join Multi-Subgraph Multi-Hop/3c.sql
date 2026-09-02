SELECT
    MIN(t.p3) AS minPaper,
    MIN(pf.fieldid) AS fieldid,
    MIN(nf.newsfeed) AS newsfeed,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
  SELECT DISTINCT
      p1.paperid AS p1,
      p3.paperid AS p3
  FROM (p1:Papers)-[r1:PaperReferences*3..3]->(p3:Papers)
  WHERE p1.paperid = 'W2122344208'
    AND p3.citation_count < 5
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.fieldid
  FROM (p:Papers)-[pf:PaperFields]->(n:Fields)
) pf
ON t.p3 = pf.paperid

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.newsfeed_id AS newsfeed
  FROM (p:Papers)-[nf:link_newsfeed]->(n:Newsfeed_Metadata)
) nf
ON t.p1 = nf.paperid

LEFT JOIN papersources ps
  ON t.p1 = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON t.p1 = ln.paperid

LEFT JOIN link_patents lp
  ON t.p1 = lp.paperid;