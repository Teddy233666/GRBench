MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(p4:Papers)
WHERE p1.paperid = 'W2122344208' AND p4.citation_count < 80
OPTIONAL MATCH (p4)-[pf:PaperFields]->(f:Fields)
RETURN MIN(p4.paperid) AS p3, MIN(CASE WHEN f IS NULL THEN NULL ELSE f.fieldid END) AS fieldid;
