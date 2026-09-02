SELECT MIN(p123.p3::text) AS p3, MIN(pf.fieldid::text) AS fieldid
FROM cypher('sciscinet_graph', $$
    MATCH (p1:Papers)-[:PaperReferences]->(:Papers)
          -[:PaperReferences]->(:Papers)-[:PaperReferences]->(p3:Papers)
    WHERE p1.paperid = 'W2122344208' AND toInteger(p3.citation_count) < 5
    RETURN p3.paperid
$$) AS p123(p3 agtype)
LEFT JOIN cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:PaperFields]->(f:Fields)
    RETURN p.paperid, f.fieldid
$$) AS pf(paper_id agtype, fieldid agtype)
ON p123.p3::text = pf.paper_id::text;
