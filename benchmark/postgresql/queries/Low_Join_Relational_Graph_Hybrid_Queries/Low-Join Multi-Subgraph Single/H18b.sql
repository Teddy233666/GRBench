SELECT
    MIN(p123.p3::text),
    MIN(nf.newsfeed::text) AS newsfeed,
    MIN(ln.laureate_id::text) AS minNobel
FROM

cypher('sciscinet_graph', $$
    MATCH (p1:Papers)-[:PaperReferences]->(p3:Papers)
    WHERE p1.paperid = 'W2122344208'
     AND toInteger(p3.citation_count)  < 80
    RETURN p1.paperid, p3.paperid
$$) AS p123(p1 agtype, p3 agtype)

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (p4:Papers)-[:link_newsfeed]->(n:Newsfeed_Metadata)
    RETURN p4.paperid, n.newsfeed_id
$$) AS nf(p4 agtype, newsfeed agtype)

ON p123.p1::text = nf.p4::text

LEFT JOIN link_nobellaureates ln
  ON p123.p1::text = ln.paperid;