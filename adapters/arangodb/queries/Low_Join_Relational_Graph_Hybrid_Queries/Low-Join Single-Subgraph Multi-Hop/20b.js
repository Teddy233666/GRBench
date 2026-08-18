var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 80
        RETURN {
          paperid: "W2122344208"
        }
)

// 保证 MIN 至少有一行（模拟 SQL）
FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: "W2122344208" }])

  // ---------- papersources（LEFT JOIN）----------
  LET pss = (
    FOR ps IN papersources
      FILTER ps.paperid == r.paperid
      RETURN ps.sourceid
  )

  // ---------- sources（LEFT JOIN）----------
  LET ss = (
    FOR s IN sources
      FILTER s.sourceid IN pss
      RETURN s.sourceid
  )

  // ---------- LEFT JOIN 展开 ----------
  FOR s IN (LENGTH(ss) > 0 ? ss : [null])

    COLLECT AGGREGATE
      minPaper = MIN(r.paperid),
      minSource = MIN(s)

RETURN {
  minPaper,
  minSource
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));