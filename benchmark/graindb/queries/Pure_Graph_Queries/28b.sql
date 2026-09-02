SELECT
    MIN(t.ref_paper_id),
    MIN(nsf.award_id)
FROM
(
  SELECT DISTINCT
      p4.paperid AS paper_id,
      ref.paperid AS ref_paper_id
  FROM (p4:Papers)-[r1:PaperReferences]->(ref:Papers)
  WHERE p4.paperid LIKE 'W423590139%'
    AND p4.citation_count <= 1
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      n.award_id
  FROM (p:Papers)-[ln:Link_NSF]->(n:NSF_Metadata)
) nsf
ON t.paper_id = nsf.paperid;