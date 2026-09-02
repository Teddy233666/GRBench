var cursor = db._query(`
LET g_ref = (
  FOR p IN Papers
    FILTER STARTS_WITH(p.paperid, "W423590139")
      AND p.citation_count ==1

    FOR n IN 1..1 OUTBOUND p Link_NIH
      RETURN { paperid: p._key }
)

FOR r IN g_ref
  COLLECT AGGREGATE cited_paperid = MIN(r.paperid)

RETURN cited_paperid
`)
var result = cursor.toArray();
print(JSON.stringify(result));