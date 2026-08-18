MATCH (p:Papers)
MATCH (p)-[r:PaperReferences]->(ref:Papers)
WHERE p.paperid = 'W4211259235' AND ref.citation_count < 150
OPTIONAL MATCH (ag:Authors_Gender)-[ap:Authors_Paper]->(p) WHERE ag.h_index > 10
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (ad:AuthorDetails) WHERE ad.authorid = ag.authorid
RETURN MIN(p.paperid) AS minPaper, MIN(CASE WHEN ag IS NULL THEN NULL ELSE ag.authorid END) AS minAuthor, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN ad IS NULL THEN NULL ELSE ad.authorid END) AS minPatent;
