MATCH (inst_0:Affiliations {institutionid:'I4210136388'})
MATCH p = allshortestpaths((inst_0)-[:affl_assoc_affl*1..]->(inst_asia:Affiliations))
WHERE inst_asia.institutionid = 'I4210088668'
RETURN MIN(inst_asia.institutionid) AS inst_asia_institutionid;
