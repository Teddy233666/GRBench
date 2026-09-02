SELECT
    MIN(t.ref_paper_id) AS minPaper,
    MIN(t2.award_id) AS award_id,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
  SELECT DISTINCT
      p4.paperid AS paper_id,
      ref.paperid AS ref_paper_id,
      ref.citation_count
  FROM (p4:Papers)-[r3:PaperReferences]->(ref:Papers)
  WHERE p4.paperid = 'W4211259235'
    AND ref.citation_count < 150
) t

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

LEFT JOIN link_patents lp
  ON t.ref_paper_id = lp.paperid;