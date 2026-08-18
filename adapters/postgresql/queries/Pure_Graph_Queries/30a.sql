SELECT
    MIN(pn.paperid::text) AS cited_paperid
FROM

cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_NSF]->(n:NSF_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND toInteger(p.citation_count) <= 3
    RETURN p.paperid
$$) AS pn(paperid agtype);