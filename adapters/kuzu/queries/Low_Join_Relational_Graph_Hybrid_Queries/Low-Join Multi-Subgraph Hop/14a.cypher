MATCH (p4:Papers)
MATCH (p4)-[r1:PaperReferences]->(p5:Papers)
MATCH (p5)-[r2:PaperReferences]->(p6:Papers)
MATCH (p6)-[r3:PaperReferences]->(ref:Papers)
WHERE p4.paperid = 'W2122344208' AND ref.citation_count < 150
OPTIONAL MATCH (ag:Authors_Gender)-[ap:Authors_Paper]->(ref) WHERE ag.h_index > 10
OPTIONAL MATCH (lnsf:link_nsf) WHERE lnsf.paperid = p4.paperid
OPTIONAL MATCH (nsf:nsf_metadata) WHERE nsf.award_id = lnsf.award_id
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p4.paperid
OPTIONAL MATCH (ad:AuthorDetails) WHERE ad.authorid = ag.authorid
RETURN MIN(p4.paperid) AS minPaper, MIN(CASE WHEN ag IS NULL THEN NULL ELSE ag.authorid END) AS minAuthor1, MIN(CASE WHEN nsf IS NULL THEN NULL ELSE nsf.award_id END) AS award_id, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN ad IS NULL THEN NULL ELSE ad.authorid END) AS minAuthorid2;
