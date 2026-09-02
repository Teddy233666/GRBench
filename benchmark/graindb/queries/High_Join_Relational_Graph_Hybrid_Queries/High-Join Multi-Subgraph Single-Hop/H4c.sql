SELECT
    MIN(t.paperid) AS minPaper,
    MIN(t1.authorid) AS minAuthor,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
  SELECT DISTINCT
      p.paperid,
      ref.paperid AS ref_paperid,
      ref.citation_count
  FROM (p:Papers)-[r1:PaperReferences]->(ref:Papers)
  WHERE p.paperid = 'W4211259235'
    AND ref.citation_count < 5
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      a.authorid
  FROM (p:Papers)-[pa:Papers_to_Authors]->(a:Authors_Gender)
  WHERE a.h_index > 80
) t1
ON t.paperid = t1.paperid

LEFT JOIN papersources ps
  ON t.ref_paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON t.paperid = ln.paperid

LEFT JOIN author_details ad
  ON t1.authorid = ad.authorid;