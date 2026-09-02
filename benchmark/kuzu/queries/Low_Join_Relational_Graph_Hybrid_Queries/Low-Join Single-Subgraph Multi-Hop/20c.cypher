MATCH (orig:Papers)
MATCH (orig)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(cited:Papers)
WHERE orig.paperid = 'W2122344208' AND cited.citation_count < 5
OPTIONAL MATCH (orig)-[ps:papersources]->(s:Sources)
RETURN MIN(orig.paperid) AS cited_paperid, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource;
