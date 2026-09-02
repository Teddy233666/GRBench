MATCH (inst_0:Affiliations {institutionid:'I4210136388'})
MATCH p = allshortestpaths((inst_0)-[:affl_assoc_affl*1..]->(inst_eu:Affiliations))
WHERE inst_eu.productivity > 48000
RETURN MIN(inst_eu.institutionid) AS inst_eu_institutionid;