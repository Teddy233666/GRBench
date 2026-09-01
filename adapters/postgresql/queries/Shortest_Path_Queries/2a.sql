SELECT MIN(inst_for_institutionid::text) AS inst_for_institutionid
FROM cypher('sciscinet_graph', $$

    MATCH p = (inst_cn:Affiliations)-[af:affl_assoc_affl*1..3]->(inst_for:Affiliations)
    WHERE inst_cn.institutionid = 'I4210136388'
      AND toFloat(inst_for.productivity) > 8000

    WITH p, inst_cn AS inst_cn_dummy, inst_for AS inst_for_dummy, length(p) AS hops

    WITH * ORDER BY hops ASC LIMIT 1

    RETURN inst_for_dummy.institutionid AS inst_for_institutionid,
           inst_cn_dummy.institutionid AS inst_cn_institutionid

$$) AS t(inst_for_institutionid agtype, inst_cn_institutionid agtype);