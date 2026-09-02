MATCH (inst_0:Affiliations {institutionid:'I4210136388'})
MATCH p = allshortestpaths((inst_0)-[:affl_assoc_affl*1..4]->(inst_asia:Affiliations))
WHERE inst_asia.institutionid = 'I4210088668'
OPTIONAL MATCH (paper:Papers)-[e:contributed_from]->(i:Affiliations {institutionid: inst_asia.institutionid})
RETURN MIN(i.institutionid) AS institutionid;
