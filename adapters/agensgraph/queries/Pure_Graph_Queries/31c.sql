SELECT
    MIN(REPLACE((p123.p3)::text, '"', '')) AS p3,
    MIN(REPLACE((pf.fieldid)::text, '"', '')) AS fieldid
FROM
(
    MATCH (p1:Papers)-[:PaperReferences]->(:Papers)
          -[:PaperReferences]->(:Papers)-[:PaperReferences]->(p3:Papers)
    WHERE p1.paperid='W2122344208' AND p3.citation_count<5
    RETURN p3.paperid AS p3
) p123
LEFT JOIN
(
    MATCH (p:Papers)-[:PaperFields]->(f:Fields)
    RETURN p.paperid AS paper_id, f.fieldid AS fieldid
) pf
ON REPLACE((p123.p3)::text, '"', '') = REPLACE((pf.paper_id)::text, '"', '');
