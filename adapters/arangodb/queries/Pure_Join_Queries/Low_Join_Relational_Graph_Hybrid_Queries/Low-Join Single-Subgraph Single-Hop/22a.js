var cursor = db._query(`
LET g_ref = (
  FOR p IN Papers
    FILTER STARTS_WITH(p.paperid, "W423590139")
      AND p.citation_count <= 3

    // 原 OUTBOUND 遍历 Link_NIH 展开为 _from/_to
    FOR edge IN Link_NIH
      FILTER edge._from == p._id
      LET n = DOCUMENT(edge._to)

    RETURN { paperid: p._key }
)

// 保证至少返回一行（模拟 SQL LEFT JOIN）
FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: null }])

  // LEFT JOIN link_nobellaureates（不变）
  LET lns = (
    FOR ln IN link_nobellaureates
      FILTER ln.paperid == r.paperid
      RETURN ln.laureate_id
  )

  // 展开 LEFT JOIN 空值兜底
  FOR ln IN (LENGTH(lns) > 0 ? lns : [null])

    COLLECT AGGREGATE
      cited_paperid = MIN(r.paperid),
      minNobel = MIN(ln)

RETURN {
  cited_paperid,
  minNobel
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));