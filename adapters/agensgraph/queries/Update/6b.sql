LOAD FROM grbench_update6_papers_to_authors AS backup
MATCH (p:Papers)-[e:Papers_to_Authors]->(a:Authors_Gender)
WHERE p.paperid = backup.paperid
  AND a.authorid = backup.authorid
DELETE e;

LOAD FROM grbench_update6_affiliated_with AS backup
MATCH (a:Authors_Gender)-[w:affiliated_with]->(i:Affiliations)
WHERE a.authorid = backup.authorid
  AND i.institutionid = backup.institutionid
DELETE w;

