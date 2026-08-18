var cursor = db._query(`
LET g_ref = (
  FOR p IN Papers
    FILTER STARTS_WITH(p.paperid, "W423590139")
      AND p.citation_count ==1
    FOR n IN 1..1 OUTBOUND p Link_NIH
      RETURN { paperid: p._key }
)

// 保证 SQL 的 MIN 行为（至少一行）
FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: null }])

  // ---------- LEFT JOIN ----------
  LET lns = (
    FOR ln IN link_nobellaureates
      FILTER ln.paperid == r.paperid
      RETURN ln.laureate_id
  )

  // ---------- 展开 LEFT JOIN ----------
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