SELECT
    MIN(g_ref.paperid),
    MIN(g_ap.award_id)
FROM
GRAPH_TABLE(
    sciscinet_graph
    MATCH (p IS Papers)-[pr IS  Link_NIH]->(n IS NIH_Metadata)
     WHERE p.paperid LIKE 'W423590139%'
      AND p.citation_count =1
    COLUMNS (
        p.paperid  AS paperid
    )
) g_ref
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH (p IS Papers)-[pr IS  Link_NSF]->(n IS NSF_Metadata)
    COLUMNS (
        p.paperid      AS paperid,
        n.award_id AS award_id
    )
) g_ap
ON g_ap.paperid= g_ref.paperid;
