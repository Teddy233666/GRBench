SELECT
    MIN(p123.p3),
    MIN(ap4.author),
    MIN(nf.newsfeed)
FROM
GRAPH_TABLE(
    sciscinet_graph
   MATCH (p1 IS Papers)-[r1 IS PaperReferences]->(p5 IS Papers)-[r2 IS PaperReferences]->(p6 IS Papers)-[r3 IS PaperReferences]->(p3 IS Papers)
     WHERE p1.paperid='W4235901390'

    COLUMNS(
        p1.paperid AS p1,
        p3.paperid AS p3
    )
) p123
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (a IS Authors_Gender)
            -[ap IS Authors_Paper]->
        (p4 IS Papers)
    COLUMNS(
        a.authorid AS author,
        p4.paperid AS p4
    )
) ap4
ON p123.p1 = ap4.p4
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (p4 IS Papers)
            -[nf IS link_newsfeed]->
        (n IS Newsfeed_Metadata)
    COLUMNS(
        p4.paperid    AS p4,
        n.newsfeed_id AS newsfeed
    )
) nf
ON p123.p1  = nf.p4;
