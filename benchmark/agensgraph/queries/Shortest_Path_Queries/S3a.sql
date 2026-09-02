MATCH (inst_cn:Affiliations {institutionid:'I4210136388'})
MATCH p = allshortestpaths((inst_cn)-[:affl_assoc_affl*1..4]->(inst_for:Affiliations))
WHERE inst_for.productivity > 8000
OPTIONAL MATCH (paper:Papers)-[e:contributed_from]->(i:Affiliations {institutionid: inst_for.institutionid})
RETURN MIN(i.institutionid) AS institutionid;