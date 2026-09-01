-- statement
MATCH (u:Update4_Authors_Gender)
MATCH (:Papers)-[r:Papers_to_Authors]->(a:Authors_Gender)
WHERE a.authorid = u.authorid
DELETE r;

-- statement
MATCH (u:Update4_Authors_Gender)
MATCH (a:Authors_Gender)-[r:affiliated_with]->(:Affiliations)
WHERE a.authorid = u.authorid
DELETE r;

-- statement
MATCH (u:Update4_Authors_Gender)
MATCH (a:Authors_Gender)
WHERE a.authorid = u.authorid
DELETE a;
