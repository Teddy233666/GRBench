var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 80
        RETURN {
          paperid: "W2122344208",
          cited_paperid: ref._key
        }
)

// 保证 SQL 的 MIN 行为（即使 g_ref 为空）
FOR r IN (LENGTH(g_ref) > 0
          ? g_ref
          : [{ paperid: "W2122344208", cited_paperid: null }])

  // ---------- LEFT JOIN h0 ----------
  LET h0s = (
    FOR h0 IN hit_papers_level0
      FILTER h0.paperid == r.paperid
      RETURN h0.fieldid
  )

  // ---------- LEFT JOIN lp ----------
  LET lps = (
    FOR lp IN link_patents
      FILTER lp.paperid == r.cited_paperid
      RETURN lp.patent
  )

  // ---------- 展开 LEFT JOIN ----------
  FOR h0 IN (LENGTH(h0s) > 0 ? h0s : [null])
    FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

      COLLECT AGGREGATE
        minPaper = MIN(r.paperid),
        minField = MIN(h0),
        minPatent = MIN(lp)

RETURN {
  minPaper,
  fieldid: minField,
  minPatent
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));