SELECT
    MIN(t.paperid) AS minPaper,
    MIN(t2.authorid) AS minAuthor1,
    MIN(t1.award_id) AS award_id,
    MIN(s.sourceid) AS minSource,
    MIN(lp.patent) AS minNobel,
    MIN(ad.authorid) AS minAuthorid2
FROM
(
  SELECT DISTINCT
      p.paperid,
      ref.paperid AS ref_paperid,
      ref.citation_count
  FROM (p:Papers)-[r1:PaperReferences*3..3]->(ref:Papers)
  WHERE p.paperid = 'W2122344208'
    AND ref.citation_count < 5
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.award_id
  FROM (p:Papers)-[e2:Link_NSF]->(nsf:NSF_Metadata)
) t1
ON t.paperid = t1.paperid

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      a.authorid
  FROM (p:Papers)-[pa:Papers_to_Authors]->(a:Authors_Gender)
  WHERE a.h_index > 80
) t2
ON t.ref_paperid = t2.paperid

LEFT JOIN papersources ps
  ON t.ref_paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_patents lp
  ON t.paperid = lp.paperid

LEFT JOIN author_details ad
  ON t2.authorid = ad.authorid;
