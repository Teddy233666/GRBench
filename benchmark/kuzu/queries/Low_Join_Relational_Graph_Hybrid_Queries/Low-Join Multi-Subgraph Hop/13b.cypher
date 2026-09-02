MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(ref:Papers)
WHERE p1.paperid = 'W2122344208' AND ref.citation_count < 80
OPTIONAL MATCH (ag:Authors_Gender)-[ap:Authors_Paper]->(p1) WHERE ag.h_index > 30
OPTIONAL MATCH (ref)-[cf:contributed_from]->(inst:Affiliations) WHERE CAST(inst.productivity AS DOUBLE) > 5000
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p1.paperid
OPTIONAL MATCH (ad:AuthorDetails) WHERE ad.authorid = ag.authorid
RETURN MIN(p1.paperid) AS minPaper, MIN(CASE WHEN ag IS NULL THEN NULL ELSE ag.authorid END) AS minAuthor, MIN(CASE WHEN inst IS NULL THEN NULL ELSE inst.institutionid END) AS minAff, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN ad IS NULL THEN NULL ELSE ad.authorid END) AS minPatent;
