SELECT MIN(g_i.institutionid)
FROM
    GRAPH_TABLE (
        sciscinet_graph
        MATCH p = ANY SHORTEST (inst_cn IS Affiliations)
            -[af IS affl_assoc_affl]->{1,4}
        (inst_for IS Affiliations)
        WHERE
         inst_cn.institutionid = 'I4210136388'
        AND inst_for.productivity>8000
        COLUMNS (
           inst_for.institutionid AS institutionid
        )
    ) g_asso
    LEFT JOIN GRAPH_TABLE (
        sciscinet_graph
        MATCH (p IS Papers)-[e IS contributed_from]->(i IS Affiliations)
        COLUMNS (
            p.paperid AS cited_id,
            i.institutionid AS institutionid
        )
    ) g_i ON g_asso.institutionid = g_i.institutionid;