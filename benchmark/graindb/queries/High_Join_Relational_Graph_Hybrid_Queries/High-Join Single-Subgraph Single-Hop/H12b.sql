SELECT
    MIN(t.paperid) AS cited_paperid,
    MIN(s.sourceid) AS minSource,
    MIN(h1.paperid) AS minh1paperid,
    MIN(lp.patent) AS minPatent
FROM
(
  SELECT DISTINCT
      p.paperid
  FROM (p IS Papers)-[pr IS Link_ClinicalTrials]->(n IS clinicaltrials_metadata)
  WHERE p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 1
) t

LEFT JOIN papersources ps
  ON t.paperid = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN hit_papers_level1 h1
  ON t.paperid = h1.paperid

LEFT JOIN link_patents lp
  ON t.paperid = lp.paperid;