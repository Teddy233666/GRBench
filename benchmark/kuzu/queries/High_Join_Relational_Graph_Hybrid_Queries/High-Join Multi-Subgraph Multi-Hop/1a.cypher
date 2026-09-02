MATCH (p:Papers)
MATCH (p)-[r1:PaperReferences]->(p1:Papers)
MATCH (p1)-[r2:PaperReferences]->(p2:Papers)
MATCH (p2)-[r3:PaperReferences]->(ref:Papers)
WHERE p.paperid = 'W2122344208' AND ref.citation_count < 150
OPTIONAL MATCH (a:Authors_Gender)-[ap:Authors_Paper]->(p) WHERE a.h_index > 10
OPTIONAL MATCH (ref)-[cf:contributed_from]->(inst:Affiliations) WHERE CAST(inst.productivity AS DOUBLE) > 1000
OPTIONAL MATCH (ref)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (ad:AuthorDetails) WHERE ad.authorid = a.authorid
RETURN MIN(p.paperid) AS minPaper, MIN(CASE WHEN a IS NULL THEN NULL ELSE a.authorid END) AS minAuthor, MIN(CASE WHEN cf IS NULL THEN NULL ELSE ref.paperid END) AS minAff, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN ad IS NULL THEN NULL ELSE ad.authorid END) AS minPatent;
