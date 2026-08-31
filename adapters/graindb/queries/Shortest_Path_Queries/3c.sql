SELECT
    MIN(g_asso.institutionid)
FROM
(
    MATCH p = shortestPath(
        (inst_cn:Affiliations)-[:affl_assoc_affl*1..4]->(inst_for:Affiliations)
    )
    WHERE inst_cn.institutionid = 'I4210136388'
      AND inst_for.institutionid = 'I4210088668'
    RETURN
        inst_for.institutionid AS institutionid,
        nodes(p) AS pathnode
) g_asso

LEFT JOIN
(
    MATCH (p:Papers)-[e:contributed_from]->(i:Affiliations)
    RETURN
        p.paperid AS cited_id,
        i.institutionid AS institutionid
) g_i
ON g_asso.institutionid = g_i.institutionid;