MATCH (inst:Affiliations)
MATCH (inst)-[r1:affl_assoc_affl]->(m1:Affiliations)
MATCH (m1)-[r2:affl_assoc_affl]->(m2:Affiliations)
MATCH (m2)-[r3:affl_assoc_affl]->(m3:Affiliations)
MATCH (m3)-[r4:affl_assoc_affl]->(assoc:Affiliations)
WHERE inst.institutionid STARTS WITH 'I42101230'
RETURN MIN(assoc.institutionid) AS associated_institutionid;
