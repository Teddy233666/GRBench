MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(p4:Papers)
WHERE p1.paperid = 'W2122344208' AND p4.citation_count < 150
OPTIONAL MATCH (ag:Authors_Gender)-[ap:Authors_Paper]->(p4) WHERE ag.h_index > 10
OPTIONAL MATCH (lnsf:link_nsf) WHERE lnsf.paperid = p1.paperid
OPTIONAL MATCH (nsf:nsf_metadata) WHERE nsf.award_id = lnsf.award_id
OPTIONAL MATCH (p4)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p1.paperid
OPTIONAL MATCH (ad:AuthorDetails) WHERE ad.authorid = ag.authorid
RETURN MIN(p1.paperid) AS minPaper, MIN(CASE WHEN ag IS NULL THEN NULL ELSE ag.authorid END) AS minAuthor1, MIN(CASE WHEN nsf IS NULL THEN NULL ELSE nsf.award_id END) AS award_id, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minNobel, MIN(CASE WHEN ad IS NULL THEN NULL ELSE ad.authorid END) AS minAuthorid2;
