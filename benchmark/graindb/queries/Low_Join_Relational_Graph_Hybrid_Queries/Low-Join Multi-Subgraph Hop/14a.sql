SELECT
    MIN(t.ref_paper_id) AS minPaper,
    MIN(t1.author_id) AS minAuthor1,
    MIN(t2.award_id) AS award_id,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minAuthorid2
FROM
(
  SELECT DISTINCT
      p4.paperid AS paper_id,
      ref.paperid AS ref_paper_id,
      ref.citation_count
  FROM (p4:Papers)-[r1:PaperReferences*3..3]->(ref:Papers)
  WHERE p4.paperid = 'W2122344208'
    AND ref.citation_count < 150
) t

LEFT JOIN
(
  SELECT DISTINCT
      a.authorid,
      p.paperid
  FROM (a:Authors_Gender)-[ap_rel:Authors_Paper]->(p:Papers)
  WHERE a.h_index > 10
) t1
ON t1.paperid = t.ref_paper_id

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.award_id
  FROM (p:Papers)-[e2:Link_NSF]->(n:NSF_Metadata)
) t2
ON t2.paperid = t.paper_id

LEFT JOIN link_nobellaureates ln
  ON t.ref_paper_id = ln.paperid

LEFT JOIN author_details ad
  ON t1.author_id = ad.authorid;