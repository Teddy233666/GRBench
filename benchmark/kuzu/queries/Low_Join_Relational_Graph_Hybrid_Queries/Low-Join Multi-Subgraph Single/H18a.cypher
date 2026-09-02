MATCH (p1:Papers)
MATCH (p1)-[r:PaperReferences]->(p3:Papers)
WHERE p1.paperid = 'W2122344208' AND p3.citation_count < 150
MATCH (lnf:link_newsfeed)
MATCH (nf:newsfeed_metadata)
MATCH (ln:link_nobellaureates)
WHERE lnf.paperid = p1.paperid AND nf.newsfeed_id = lnf.newsfeed_id AND ln.paperid = p1.paperid
RETURN MIN(p3.paperid) AS p3, MIN(nf.newsfeed_id) AS newsfeed, MIN(ln.laureate_id) AS minNobel;
