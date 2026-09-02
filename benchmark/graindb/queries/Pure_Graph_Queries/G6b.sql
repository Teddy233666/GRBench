  SELECT MIN(p.paperid)
  FROM (p:Papers)-[pr:Link_NSF]->(n:NSF_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 1;