var cursor = db._query(`
FOR p IN Papers
  FILTER STARTS_WITH(p.paperid, "W423590139")
    AND p.citation_count <= 3

  FOR n IN 1..1 OUTBOUND p Link_NSF

  COLLECT AGGREGATE cited_paperid = MIN(p._key)

RETURN cited_paperid
`)
var result = cursor.toArray();
print(JSON.stringify(result));