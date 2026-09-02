SELECT
    MIN(pn.paperid::text) AS cited_paperid
FROM

cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_NIH]->(n:NIH_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND toInteger(p.citation_count) =1
    RETURN p.paperid
$$) AS pn(paperid agtype);