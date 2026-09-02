MATCH (p1:Papers)
MATCH (p1)-[r:PaperReferences]->(p3:Papers)
WHERE p1.paperid = 'W2122344208' AND p3.citation_count < 80
OPTIONAL MATCH (lnf:link_newsfeed) WHERE lnf.paperid = p1.paperid
OPTIONAL MATCH (nf:newsfeed_metadata) WHERE nf.newsfeed_id = lnf.newsfeed_id
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p1.paperid
RETURN MIN(p3.paperid) AS p3, MIN(CASE WHEN nf IS NULL THEN NULL ELSE nf.newsfeed_id END) AS newsfeed, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel;
