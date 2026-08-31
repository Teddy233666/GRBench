var cursor = db._query(`
LET g_ref = (
  // 第一层遍历：起点 -> v1（原 OUTBOUND 1 层）
  FOR edge1 IN PaperReferences
    FILTER edge1._from == "Papers/W2122344208"
    LET v1 = DOCUMENT(edge1._to)

  // 第二层遍历：v1 -> v2（原 OUTBOUND 2 层）
  FOR edge2 IN PaperReferences
    FILTER edge2._from == v1._id
    LET v2 = DOCUMENT(edge2._to)

  // 第三层遍历：v2 -> ref（原 OUTBOUND 3 层）
  FOR edge3 IN PaperReferences
    FILTER edge3._from == v2._id
    LET ref = DOCUMENT(edge3._to)

    FILTER ref.citation_count < 5

    RETURN {
      paperid: "W2122344208",
      cited_paperid: ref._key
    }
)

FOR r IN (LENGTH(g_ref) > 0
          ? g_ref
          : [{ paperid: "W2122344208", cited_paperid: null }])

  // Nobel 关联 cited_paperid
  LET lns = (
    FOR ln IN link_nobellaureates
      FILTER ln.paperid == r.cited_paperid
      RETURN ln.laureate_id
  )

  // Patent 关联原始 paperid
  LET lps = (
    FOR lp IN link_patents
      FILTER lp.paperid == r.paperid
      RETURN lp.patent
  )

  // LEFT JOIN 空值兜底
  FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
    FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

    COLLECT AGGREGATE
      minPaper = MIN(r.paperid),
      minNobel = MIN(ln),
      minPatent = MIN(lp)

RETURN {
  cited_paperid: minPaper,
  minNobel,
  minPatent
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));