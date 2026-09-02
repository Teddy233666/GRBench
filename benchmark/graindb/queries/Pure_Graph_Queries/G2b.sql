  SELECT MIN(p.paperid)
  FROM (p:Papers)-[pr:Link_NIH]->(n:NIH_Metadata)
  WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 1;