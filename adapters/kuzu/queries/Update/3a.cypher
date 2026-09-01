-- statement
MATCH (u:Update1_Papers)
MATCH (p:Papers)-[r:PaperReferences]->(:Papers)
WHERE p.paperid = u.paperid
DELETE r;

-- statement
MATCH (u:Update1_Papers)
MATCH (:Papers)-[r:PaperReferences]->(p:Papers)
WHERE p.paperid = u.paperid
DELETE r;

-- statement
MATCH (u:Update1_Papers)
MATCH (p:Papers)-[r:Papers_to_Authors]->(:Authors_Gender)
WHERE p.paperid = u.paperid
DELETE r;

-- statement
MATCH (u:Update1_Papers)
MATCH (p:Papers)-[r:contributed_from]->(:Affiliations)
WHERE p.paperid = u.paperid
DELETE r;

-- statement
MATCH (u:Update1_Papers)
MATCH (p:Papers)-[r:PaperFields]->(:Fields)
WHERE p.paperid = u.paperid
DELETE r;

-- statement
MATCH (u:Update1_Papers)
MATCH (n:link_nsf)
WHERE n.paperid = u.paperid
DELETE n;

-- statement
MATCH (u:Update1_Papers)
MATCH (n:link_nih)
WHERE n.paperid = u.paperid
DELETE n;

-- statement
MATCH (u:Update1_Papers)
MATCH (n:link_clinicaltrials)
WHERE n.paperid = u.paperid
DELETE n;

-- statement
MATCH (u:Update1_Papers)
MATCH (n:link_newsfeed)
WHERE n.paperid = u.paperid
DELETE n;

-- statement
MATCH (u:Update1_Papers)
MATCH (p:Papers)-[r:link_twitter]->(:Twitter_Metadata)
WHERE p.paperid = u.paperid
DELETE r;

-- statement
MATCH (p:Papers)
WHERE p.year >= 2020 AND p.year <= 2025
DETACH DELETE p;
