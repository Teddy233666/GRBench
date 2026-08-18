SELECT
    MIN(assoc.associated_institutionid::text) AS associated_institutionid
FROM

cypher('sciscinet_graph', $$
    MATCH (inst:Affiliations)-[:affl_assoc_affl]->(m1:Affiliations)
          -[:affl_assoc_affl]->(m2:Affiliations)
          -[:affl_assoc_affl]->(m3:Affiliations)
          -[:affl_assoc_affl]->(assoc:Affiliations)
    WHERE inst.institutionid STARTS WITH 'I42101230'
    AND  toInteger(assoc.h_index)   >= 1000
    RETURN inst.institutionid, assoc.institutionid
$$) AS assoc(institutionid agtype, associated_institutionid agtype);