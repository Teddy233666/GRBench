SELECT
    MIN(g.inst_cn_institutionid)
FROM
(
    MATCH p = shortestPath(
        (inst_cn:Affiliations)-[:affl_assoc_affl*]->(inst_for:Affiliations)
    )
    WHERE inst_cn.institutionid = 'I4210136388'
      AND inst_for.productivity > 8000
    RETURN
        inst_cn.institutionid AS inst_cn_institutionid,
        inst_for.institutionid AS inst_for_institutionid,
        relationships(p) AS edges
) g;