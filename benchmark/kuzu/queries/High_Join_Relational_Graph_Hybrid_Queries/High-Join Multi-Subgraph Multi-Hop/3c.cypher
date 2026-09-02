MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(p4:Papers)
WHERE p1.paperid = 'W2122344208' AND p4.citation_count < 5
OPTIONAL MATCH (p4)-[pf:PaperFields]->(f:Fields)
OPTIONAL MATCH (lnf:link_newsfeed) WHERE lnf.paperid = p4.paperid
OPTIONAL MATCH (nm:newsfeed_metadata) WHERE nm.newsfeed_id = lnf.newsfeed_id
OPTIONAL MATCH (p1)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p1.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p1.paperid
RETURN MIN(p4.paperid) AS p3, MIN(CASE WHEN f IS NULL THEN NULL ELSE f.fieldid END) AS fieldid, MIN(CASE WHEN nm IS NULL THEN NULL ELSE nm.newsfeed_id END) AS newsfeed, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
