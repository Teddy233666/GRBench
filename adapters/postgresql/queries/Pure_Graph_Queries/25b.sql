SELECT
    MIN(tri.inst_0_institutionid::text)
FROM

cypher('sciscinet_graph', $$
    MATCH (inst0:Affiliations)-[:affl_assoc_affl]->(inst1:Affiliations)
          -[:affl_assoc_affl]->(inst2:Affiliations)
          -[:affl_assoc_affl]->(inst3:Affiliations)
    WHERE inst0.institutionid STARTS WITH 'I42101230'
    AND toInteger(inst3.h_index)  >= 1000
    RETURN inst0.institutionid
$$) AS tri(inst_0_institutionid agtype);