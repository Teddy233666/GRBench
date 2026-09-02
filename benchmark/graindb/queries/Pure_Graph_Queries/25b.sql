SELECT  MIN(inst0.institutionid)
  FROM (inst0:Affiliations)-[af1:affl_assoc_affl*3..3]->(inst3:Affiliations)
  WHERE inst0.institutionid LIKE 'I42101230%'
  AND inst3.h_index  >= 1000;