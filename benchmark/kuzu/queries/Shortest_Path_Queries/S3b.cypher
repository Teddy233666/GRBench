MATCH p = (inst_cn:Affiliations)-[:affl_assoc_affl{{DEPTH_RANGE}}]->(inst_for:Affiliations)
WHERE inst_cn.institutionid = 'I4210136388'
  AND CAST(inst_for.productivity AS DOUBLE) > 48000
WITH DISTINCT inst_for.institutionid AS institutionid
OPTIONAL MATCH (:Papers)-[:contributed_from]->(i:Affiliations)
WHERE i.institutionid = institutionid
RETURN count(institutionid) AS matched_count,
       min(i.institutionid) AS min_joined_institutionid;
