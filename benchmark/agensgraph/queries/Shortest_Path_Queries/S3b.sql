MATCH (inst_0:Affiliations {institutionid:'I4210136388'})
MATCH p = allshortestpaths((inst_0)-[:affl_assoc_affl*1..4]->(inst_eu:Affiliations))
WHERE inst_eu.productivity > 48000
OPTIONAL MATCH (paper:Papers)-[e:contributed_from]->(i:Affiliations {institutionid: inst_eu.institutionid})
RETURN MIN(i.institutionid) AS institutionid;
