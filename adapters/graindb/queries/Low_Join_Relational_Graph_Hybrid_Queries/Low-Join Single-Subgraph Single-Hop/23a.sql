SELECT
    MIN(t.paperid) AS cited_paperid,
    MIN(lp.patent) AS minpatent
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p IS Papers)-[pr IS  Link_NSF]->(n IS NSF_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 3
) t

LEFT JOIN link_patents lp
  ON t.paperid = lp.paperid;
