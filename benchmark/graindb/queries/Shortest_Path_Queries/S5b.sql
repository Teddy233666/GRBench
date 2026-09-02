SELECT
    MIN(g_asso.institutionid)
FROM
(
    MATCH p = shortestPath(
        (inst_cn:Affiliations)-[:affl_assoc_affl*1..4]->(inst_for:Affiliations)
    )
    WHERE inst_cn.institutionid = 'I4210136388'
      AND inst_for.productivity > 48000
    RETURN
        inst_for.institutionid AS institutionid,
        relationships(p) AS edges
) g_asso

LEFT JOIN
(
    MATCH (a:Authors_Gender)-[:affiliated_with]->(i:Affiliations)
    RETURN
        a.authorid AS cited_id,
        i.institutionid AS institutionid
) g_i
ON g_asso.institutionid = g_i.institutionid;