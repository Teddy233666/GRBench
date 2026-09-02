var cursor = db._query(`
LET start = DOCUMENT("Papers/W4211259235")

LET g_ref = (
  FOR ref IN 1..1 OUTBOUND start PaperReferences
    FILTER ref.citation_count < 5
    RETURN {
      paper: start,        // ❗关键：直接传 document，不拼字符串
      ref: ref
    }
)

FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paper: start, ref: null }])

  // =====================
  // Authors_Paper (g_ap)
  // =====================
  LET aps = (
    FOR a IN 1..1 INBOUND r.paper Authors_Paper
      FILTER a.h_index > 80
      RETURN a._key
  )

  // =====================
  // Nobel
  // =====================
  LET lns = (
    FOR ln IN link_nobellaureates
      FILTER ln.paperid == r.paper._key
      RETURN ln.laureate_id
  )

  // =====================
  // author_details
  // =====================
  LET ads = (
    FOR ad IN author_details
      FILTER ad.authorid IN aps
      RETURN ad.authorid
  )

  // =====================
  // simulate LEFT JOIN expansion
  // =====================
  FOR a IN (LENGTH(aps) > 0 ? aps : [null])
    FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
      FOR ad IN (LENGTH(ads) > 0 ? ads : [null])

        COLLECT AGGREGATE
          minPaper = MIN(r.paper._key),
          minAuthor = MIN(a),
          minNobel = MIN(ln),
          minPatent = MIN(ad)

RETURN {
  minPaper,
  minAuthor,
  minNobel,
  minPatent
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));
