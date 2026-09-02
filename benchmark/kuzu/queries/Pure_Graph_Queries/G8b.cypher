MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p5:Papers)
MATCH (p5)-[r2:PaperReferences]->(p6:Papers)
MATCH (p6)-[r3:PaperReferences]->(p3:Papers)
WHERE p1.paperid = 'W4235901390' AND p6.citation_count < 100
OPTIONAL MATCH (a:Authors_Gender)-[ap:Authors_Paper]->(p1)
OPTIONAL MATCH (ln:link_newsfeed)
OPTIONAL MATCH (n:newsfeed_metadata)
WHERE ln.paperid = p1.paperid AND n.newsfeed_id = ln.newsfeed_id
RETURN MIN(p3.paperid) AS min_ref_paperid, MIN(a.authorid) AS author, MIN(n.newsfeed_id) AS newsfeed;
