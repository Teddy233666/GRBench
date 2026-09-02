var cursor = db._query(`
LET start = DOCUMENT("Papers/W2122344208")

// 原 OUTBOUND start PaperReferences 等价展开
LET g_ref = (
  FOR edge IN PaperReferences
    FILTER edge._from == start._id       // OUTBOUND = 边的_from 是起点
    LET ref = DOCUMENT(edge._to)         // 终点就是 ref 文档
    FILTER ref.citation_count < 150
    RETURN {
      p1: start._key,
      p3: ref._key
    }
)

FOR r IN g_ref

  // 原 OUTBOUND CONCAT("Papers/", r.p1) link_newsfeed 等价展开
  FOR nf IN (
    FOR edge IN link_newsfeed
      FILTER edge._from == CONCAT("Papers/", r.p1)
      LET n = DOCUMENT(edge._to)
      RETURN n.newsfeed_id
  )

  // 原 link_nobellaureates 直接过滤（无遍历）
  FOR ln IN (
    FOR l IN link_nobellaureates
      FILTER l.paperid == r.p1
      RETURN l.laureate_id
  )

  COLLECT AGGREGATE
    minPaper = MIN(r.p3),
    minNewsfeed = MIN(nf),
    minNobel = MIN(ln)

RETURN {
  minPaper,
  newsfeed: minNewsfeed,
  minNobel
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));