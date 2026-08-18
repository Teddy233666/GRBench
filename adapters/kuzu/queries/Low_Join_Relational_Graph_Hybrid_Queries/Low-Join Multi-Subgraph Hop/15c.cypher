MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p5:Papers)
MATCH (p5)-[r2:PaperReferences]->(p6:Papers)
MATCH (p6)-[r3:PaperReferences]->(p3:Papers)
WHERE p1.paperid = 'W2122344208' AND p3.citation_count < 5
OPTIONAL MATCH (p3)-[pf:PaperFields]->(f:Fields)
OPTIONAL MATCH (lnf:link_newsfeed) WHERE lnf.paperid = p1.paperid
OPTIONAL MATCH (nf:newsfeed_metadata) WHERE nf.newsfeed_id = lnf.newsfeed_id
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p1.paperid
RETURN MIN(p3.paperid) AS p3, MIN(CASE WHEN f IS NULL THEN NULL ELSE f.fieldid END) AS fieldid, MIN(CASE WHEN nf IS NULL THEN NULL ELSE nf.newsfeed_id END) AS newsfeed, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel;
