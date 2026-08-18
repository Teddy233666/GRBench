SELECT
    MIN(p123.p3),
    MIN(pf.fieldid) AS fieldid
FROM
GRAPH_TABLE(
    sciscinet_graph
   MATCH (p1 IS Papers)-[r1 IS PaperReferences]->(p5 IS Papers)-[r2 IS PaperReferences]->(p6 IS Papers)-[r3 IS PaperReferences]->(p3 IS Papers)
   WHERE p1.paperid='W2122344208'
   AND p3.citation_count<80
    COLUMNS(
        p1.paperid AS p1,
        p3.paperid AS p3
    )
) p123
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (p2 IS Papers)
            -[ln IS PaperFields]->
        (n IS Fields)

    COLUMNS(
        p2.paperid            AS paper_id,
        n.fieldid            AS fieldid
    )
) pf
ON p123.p3 = pf.paper_id;