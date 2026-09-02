SELECT
    MIN(t.p3) AS minPaper,
    MIN(pf.fieldid) AS fieldid,
    MIN(nf.newsfeed) AS newsfeed,
    MIN(ln.laureate_id) AS minNobel
FROM
(
  SELECT DISTINCT
      p1.paperid AS p1,
      p3.paperid AS p3,
      p3.citation_count
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

LEFT JOIN link_nobellaureates ln
  ON t.p1 = ln.paperid;