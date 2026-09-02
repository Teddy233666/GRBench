LOAD FROM grbench_update2_edges  AS e
MATCH (p1:Papers), (p2:Papers)
WHERE p1.paperid = e.citing_paperid
  AND p2.paperid = e.cited_paperid
MERGE (p1)-[:PaperReferences]->(p2);
