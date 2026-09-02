var cursor = db._query(`
LET g_ref = (
  // 第一层遍历：起点 → v1
  FOR edge1 IN PaperReferences
    FILTER edge1._from == "Papers/W2122344208"
    LET v1 = DOCUMENT(edge1._to)

  // 第二层遍历：v1 → v2
  FOR edge2 IN PaperReferences
    FILTER edge2._from == v1._id
    LET v2 = DOCUMENT(edge2._to)

  // 第三层遍历：v2 → ref
  FOR edge3 IN PaperReferences
    FILTER edge3._from == v2._id
    LET ref = DOCUMENT(edge3._to)

    FILTER ref.citation_count < 80

    RETURN {
      paperid: "W2122344208",
      cited_paperid: ref._key
    }
)

// 保证至少返回一行（模拟 SQL LEFT JOIN）
FOR r IN (LENGTH(g_ref) > 0
          ? g_ref
          : [{ paperid: "W2122344208", cited_paperid: null }])

  // hit_papers_level0 关联（不变）
  LET h0s = (
    FOR h0 IN hit_papers_level0
      FILTER h0.paperid == r.paperid
      RETURN h0.fieldid
  )

  // link_patents 关联（不变）
  LET lps = (
    FOR lp IN link_patents
      FILTER lp.paperid == r.cited_paperid
      RETURN lp.patent
  )

  // LEFT JOIN 空值兜底
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