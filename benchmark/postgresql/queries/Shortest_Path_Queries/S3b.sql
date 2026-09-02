SELECT MIN(g_i.institutionid::text) AS institutionid
FROM
    (SELECT * FROM cypher('sciscinet_graph', $$
        MATCH p = (inst_cn:Affiliations)-[af:affl_assoc_affl*1..4]->(inst_for:Affiliations)
        WHERE inst_cn.institutionid = 'I4210136388'
          AND toFloat(inst_for.productivity) > 48000
        WITH p, inst_cn AS inst_cn_dummy, inst_for AS inst_for_dummy, length(p) AS hops
        WITH * ORDER BY hops ASC LIMIT 1
        RETURN inst_for_dummy.institutionid AS institutionid
    $$) AS t(g_asso_institutionid agtype)) g_asso
    LEFT JOIN
    (SELECT * FROM cypher('sciscinet_graph', $$
        MATCH (p:Papers)-[e:contributed_from]->(i:Affiliations)
        RETURN p.paperid AS cited_id, i.institutionid AS institutionid
    $$) AS t(cited_id agtype, institutionid agtype)) g_i
    ON g_asso.g_asso_institutionid = g_i.institutionid;