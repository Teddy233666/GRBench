MATCH (p:Papers)
MATCH (p)-[r1:PaperReferences]->(ref:Papers)
WHERE p.paperid = 'W4211259235' AND ref.citation_count < 80
OPTIONAL MATCH (ag:Authors_Gender)-[ap:Authors_Paper]->(p) WHERE ag.h_index > 30
OPTIONAL MATCH (ref)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (ad:AuthorDetails) WHERE ad.authorid = ag.authorid
RETURN MIN(p.paperid) AS minPaper, MIN(CASE WHEN ag IS NULL THEN NULL ELSE ag.authorid END) AS minAuthor, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN ad IS NULL THEN NULL ELSE ad.authorid END) AS minPatent;
