SELECT
    MIN(t.paperid) AS minPaper,
    MIN(t2.authorid) AS minAuthor,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p:Papers)-[r1:PaperReferences]->(ref:Papers)
  WHERE p.paperid = 'W4211259235'
    AND ref.citation_count < 5
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      a.authorid
  FROM (a:Authors_Gender)-[ap:Authors_Paper]->(p:Papers)
  WHERE a.h_index > 80
) t2
ON t.paperid = t2.paperid

LEFT JOIN link_nobellaureates ln
  ON t.paperid = ln.paperid

LEFT JOIN author_details ad
  ON t2.authorid = ad.authorid;