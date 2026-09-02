MATCH (inst0:Affiliations)
MATCH (inst0)-[af1:affl_assoc_affl]->(inst1:Affiliations)
MATCH (inst1)-[af2:affl_assoc_affl]->(inst2:Affiliations)
MATCH (inst2)-[af3:affl_assoc_affl]->(inst3:Affiliations)
WHERE inst0.institutionid STARTS WITH 'I42101230'
RETURN MIN(inst0.institutionid) AS inst_0_institutionid;
