SELECT
    MIN(t.p3),
    MIN(t1.author),
    MIN(t2.newsfeed)
FROM
(
  SELECT DISTINCT
      p.paperid AS p1,
      ref.paperid AS p3
  FROM (p:Papers)-[r1:PaperReferences]->(p5:Papers)
       -[r2:PaperReferences]->(p6:Papers)
       -[r3:PaperReferences]->(ref:Papers)
  WHERE p.paperid = 'W4235901390'
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      a.authorid AS author
  FROM (p:Papers)-[pa:Papers_to_Authors]->(a:Authors_Gender)
   WHERE p.paperid = 'W4235901390'
) t1
ON t.p1 = t1.paperid

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.newsfeed_id AS newsfeed
  FROM (p:Papers)-[nf:link_newsfeed]->(n:Newsfeed_Metadata)
   WHERE p.paperid = 'W4235901390'
) t2
ON t.p1 = t2.paperid;
