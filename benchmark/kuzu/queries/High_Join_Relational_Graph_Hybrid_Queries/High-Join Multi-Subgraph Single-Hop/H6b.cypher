MATCH (p:Papers)
MATCH (p)-[r1:PaperReferences]->(ref:Papers)
WHERE p.paperid = 'W4211259235' AND ref.citation_count < 80
OPTIONAL MATCH (lnf:link_newsfeed) WHERE lnf.paperid = p.paperid
OPTIONAL MATCH (nm:newsfeed_metadata) WHERE nm.newsfeed_id = lnf.newsfeed_id
OPTIONAL MATCH (p)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p.paperid
RETURN MIN(ref.paperid) AS p3, MIN(CASE WHEN nm IS NULL THEN NULL ELSE nm.newsfeed_id END) AS newsfeed, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
