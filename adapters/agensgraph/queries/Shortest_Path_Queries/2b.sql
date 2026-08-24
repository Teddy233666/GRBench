MATCH (inst_cn:Affiliations {institutionid:'I4210136388'})
MATCH p = allshortestpaths((inst_cn)-[:affl_assoc_affl*1..3]->(inst_for:Affiliations))
WHERE inst_for.productivity > 48000
RETURN MIN(inst_for.institutionid) AS inst_for_institutionid;