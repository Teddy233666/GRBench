SELECT
    MIN(pn.paperid)            AS cited_paperid
FROM
GRAPH_TABLE(
    sciscinet_graph
    MATCH (p IS Papers)-[pr IS  Link_NSF]->(n IS NSF_Metadata)
     WHERE p.paperid LIKE 'W423590139%'
      AND p.citation_count <=1
    COLUMNS (
        p.paperid AS paperid
    )
) pn;