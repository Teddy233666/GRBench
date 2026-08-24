LOAD FROM grbench_update5_papers_to_authors AS e
MATCH (p:Papers)-[r:Papers_to_Authors]->(a:Authors_Gender)
WHERE p.paperid = e.paperid
  AND a.authorid = e.authorid
DELETE r;