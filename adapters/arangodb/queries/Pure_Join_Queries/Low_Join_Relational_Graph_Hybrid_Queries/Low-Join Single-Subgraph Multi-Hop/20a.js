var cursor = db._query(`
LET g_ref = (
  // 第一层遍历：起点 -> v1
  FOR edge1 IN PaperReferences
    FILTER edge1._from == "Papers/W2122344208"
    LET v1 = DOCUMENT(edge1._to)

  // 第二层遍历：v1 -> v2
  FOR edge2 IN PaperReferences
    FILTER edge2._from == v1._id
    LET v2 = DOCUMENT(edge2._to)

  // 第三层遍历：v2 -> ref
  FOR edge3 IN PaperReferences
    FILTER edge3._from == v2._id
    LET ref = DOCUMENT(edge3._to)

    FILTER ref.citation_count < 150

    RETURN {
      paperid: "W2122344208"
    }
)

// 保证至少返回一行
FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: "W2122344208" }])

  // papersources 关联（不变）
  LET pss = (
    FOR ps IN papersources
      FILTER ps.paperid == r.paperid
      RETURN ps.sourceid
  )

  // sources 关联（不变）
  LET ss = (
    FOR s IN sources
      FILTER s.sourceid IN pss
      RETURN s.sourceid
  )

  // LEFT JOIN 空值兜底
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