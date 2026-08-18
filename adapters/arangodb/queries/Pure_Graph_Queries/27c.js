var cursor = db._query(`
FOR p IN Papers
  FILTER STARTS_WITH(p.paperid, "W423590139")
    AND p.citation_count ==1
  FOR n IN 1..1 OUTBOUND p Link_NIH
  LET nsf = (
    FOR n2 IN 1..1 OUTBOUND p Link_NSF
      RETURN 1
  )
  COLLECT AGGREGATE minPaper = MIN(p.paperid)

RETURN minPaper
`)
var result = cursor.toArray();
print(JSON.stringify(result));