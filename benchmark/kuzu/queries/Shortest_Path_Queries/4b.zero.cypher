MATCH (inst_for:Affiliations)
WHERE inst_for.institutionid = 'I4210136388'
  AND CAST(inst_for.productivity AS DOUBLE) > 48000
RETURN count(inst_for.institutionid) AS matched_count,
       min(inst_for.institutionid) AS min_institutionid;
