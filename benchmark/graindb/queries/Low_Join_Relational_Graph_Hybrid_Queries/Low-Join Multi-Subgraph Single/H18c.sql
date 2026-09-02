SELECT
    MIN(t.p3) AS minPaper,
    MIN(t2.newsfeed) AS newsfeed,
    MIN(ln.laureate_id) AS minNobel
FROM
(
  SELECT DISTINCT
      p1.paperid AS p1,
      p3.paperid AS p3,
      p3.citation_count
  FROM (p1:Papers)-[r1:PaperReferences]->(p3:Papers)
  WHERE p1.paperid = 'W2122344208'
    AND p3.citation_count < 5
) t

JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.newsfeed_id AS newsfeed
  FROM (p:Papers)-[nf:link_newsfeed]->(n:Newsfeed_Metadata)
) t2
ON t.p1 = t2.paperid

JOIN link_nobellaureates ln
  ON t.p1 = ln.paperid;