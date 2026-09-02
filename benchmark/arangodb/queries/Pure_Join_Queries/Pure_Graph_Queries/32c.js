var cursor =  db._query(`
LET g_ref = (
  // 第一层：起点 → v1
  FOR edge1 IN PaperReferences
    FILTER edge1._from == "Papers/W2122344208"
    LET v1 = DOCUMENT(edge1._to)

  // 第二层：v1 → v2
  FOR edge2 IN PaperReferences
    FILTER edge2._from == v1._id
    LET v2 = DOCUMENT(edge2._to)

  // 第三层：v2 → ref
  FOR edge3 IN PaperReferences
    FILTER edge3._from == v2._id
    LET ref = DOCUMENT(edge3._to)

    FILTER ref.citation_count < 5

    RETURN {
      paperid: "W2122344208",
      ref_paperid: ref._key
    }
)

FOR r IN (LENGTH(g_ref) > 0
          ? g_ref
          : [{ paperid: "W2122344208", ref_paperid: null }])

  // ---------- ap（作者：INBOUND 展开）----------
  LET aps = (
    FOR edge IN Authors_Paper
      FILTER edge._to == CONCAT("Papers/", r.ref_paperid)
      LET a = DOCUMENT(edge._from)
      RETURN a._key
  )

  // ---------- nsf（OUTBOUND 展开）----------
  LET nsfs = (
    FOR edge IN link_newsfeed
      FILTER edge._from == CONCAT("Papers/", r.paperid)
      LET aff = DOCUMENT(edge._to)
      RETURN aff.newsfeed_id
  )

  // ---------- LEFT JOIN ----------
  FOR a IN (LENGTH(aps) > 0 ? aps : [null])
  FOR nsf IN (LENGTH(nsfs) > 0 ? nsfs : [null])

    COLLECT AGGREGATE
      minPaper = MIN(r.paperid),
      minAuthor = MIN(a),
      minNSF = MIN(nsf)

RETURN {
  minPaper,
  minAuthor,
  minNSF
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));