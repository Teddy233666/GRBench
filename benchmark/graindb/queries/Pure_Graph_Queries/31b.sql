SELECT MIN(t.p3) AS p3, MIN(pf.fieldid) AS fieldid
FROM (
  SELECT p1.paperid AS p1, p3.paperid AS p3
  FROM (p1:Papers)-[:PaperReferences*3..3]->(p3:Papers)
  WHERE p1.paperid = 'W2122344208' AND p3.citation_count < 80
) t
LEFT JOIN (
  SELECT p.paperid, f.fieldid
  FROM (p:Papers)-[:PaperFields]->(f:Fields)
) pf ON t.p3 = pf.paperid;
