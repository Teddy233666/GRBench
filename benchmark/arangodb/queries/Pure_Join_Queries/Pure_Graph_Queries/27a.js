var cursor = db._query(`
FOR p IN Papers
  FILTER STARTS_WITH(p.paperid, "W423590139")
    AND p.citation_count <= 3

  // 原 OUTBOUND p Link_NIH 展开
  FOR edge1 IN Link_NIH
    FILTER edge1._from == p._id
    LET n = DOCUMENT(edge1._to)

  // 原 OUTBOUND p Link_NSF 展开
  LET nsf = (
    FOR edge2 IN Link_NSF
      FILTER edge2._from == p._id
      LET n2 = DOCUMENT(edge2._to)
      RETURN 1
  )

  COLLECT AGGREGATE minPaper = MIN(p.paperid)

RETURN minPaper
`)
var result = cursor.toArray();
print(JSON.stringify(result));