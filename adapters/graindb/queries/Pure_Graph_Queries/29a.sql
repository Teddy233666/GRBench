SELECT  MIN(inst0.institutionid)
  FROM (inst0:Affiliations)-[af1:affl_assoc_affl*4..4]->(inst3:Affiliations)
  WHERE inst0.institutionid LIKE 'I42101230%';
