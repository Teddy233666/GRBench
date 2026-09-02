var cursor = db._query(`
FOR inst0 IN Affiliations
  FILTER STARTS_WITH(inst0.institutionid, "I42101230")

  FOR inst1 IN 1..1 OUTBOUND inst0 affl_assoc_affl
    FOR inst2 IN 1..1 OUTBOUND inst1 affl_assoc_affl
      FOR inst3 IN 1..1 OUTBOUND inst2 affl_assoc_affl

  COLLECT AGGREGATE minInst = MIN(inst0.institutionid)

RETURN minInst
`)
var result = cursor.toArray();
print(JSON.stringify(result));