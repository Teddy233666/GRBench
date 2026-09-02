SELECT
    MIN(p123.p3::text),
    MIN(ap4.author::text),
    MIN(nf.newsfeed::text)
FROM

cypher('sciscinet_graph', $$
    MATCH (p1:Papers)-[:PaperReferences]->(p5:Papers)
          -[:PaperReferences]->(p6:Papers)
          -[:PaperReferences]->(p3:Papers)
    WHERE p1.paperid = 'W4235901390'
    AND toInteger(p6.citation_count)<100
    RETURN p1.paperid, p3.paperid
$$) AS p123(p1 agtype, p3 agtype)

LEFT JOIN

cypher('sciscinet_graph', $$
    MATCH (a:Authors_Gender)-[:Authors_Paper]->(p4:Papers)
    WHERE p4.is_retracted = FALSE
    RETURN a.authorid, p4.paperid
$$) AS ap4(author agtype, p4 agtype)

ON p123.p1::text = ap4.p4::text

LEFT JOIN

cypher('sciscinet_graph', $$
    MATCH (p4:Papers)-[:link_newsfeed]->(n:Newsfeed_Metadata)
    RETURN p4.paperid, n.newsfeed_id
$$) AS nf(p4 agtype, newsfeed agtype)

ON p123.p1::text = nf.p4::text;
