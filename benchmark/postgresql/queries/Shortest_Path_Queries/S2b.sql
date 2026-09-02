SELECT MIN(inst_eu_institutionid::text) AS inst_eu_institutionid
FROM cypher('sciscinet_graph', $$

    MATCH p = (inst_0:Affiliations)-[af:affl_assoc_affl*1..3]->(inst_eu:Affiliations)
    WHERE inst_0.institutionid = 'I4210136388'
      AND toFloat(inst_eu.productivity) > 48000

    WITH p, inst_0 AS inst_0_dummy, inst_eu AS inst_eu_dummy, length(p) AS hops

    WITH * ORDER BY hops ASC LIMIT 1

    RETURN inst_eu_dummy.institutionid AS inst_eu_institutionid,
           inst_0_dummy.institutionid AS inst_0_institutionid

$$) AS t(inst_eu_institutionid agtype, inst_0_institutionid agtype);