var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 5
        RETURN {
          paperid: "W2122344208",
          ref_paperid: ref._key
        }
)

FOR r IN (LENGTH(g_ref) > 0
          ? g_ref
          : [{ paperid: "W2122344208", ref_paperid: null }])

  // ---------- g_ap（Authors）----------
  LET aps = (
    FOR a IN 1..1 INBOUND CONCAT("Papers/", r.paperid) Authors_Paper
      FILTER a.h_index > 80
      RETURN a._key
  )

  // ---------- g_cf（Affiliation → 返回 paperid，不是机构id！）----------
  LET cfs = (
    FOR aff IN 1..1 OUTBOUND CONCAT("Papers/", r.ref_paperid) contributed_from
      FILTER aff.productivity > 10000
      RETURN r.ref_paperid   // ⭐关键修复
  )

  // ---------- Nobel ----------
  LET lns = (
    FOR ln IN link_nobellaureates
      FILTER ln.paperid == r.paperid
      RETURN ln.laureate_id
  )

  // ---------- author_details ----------
  LET ads = (
    FOR ad IN author_details
      FILTER ad.authorid IN aps
      RETURN ad.authorid
  )

  // ---------- LEFT JOIN 展开 ----------
  FOR a IN (LENGTH(aps) > 0 ? aps : [null])
    FOR cf IN (LENGTH(cfs) > 0 ? cfs : [null])
      FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
        FOR ad IN (LENGTH(ads) > 0 ? ads : [null])

          COLLECT AGGREGATE
            minPaper = MIN(r.paperid),
            minAuthor = MIN(a),
            minAff = MIN(cf),
            minNobel = MIN(ln),
            minPatent = MIN(ad)

RETURN {
  minPaper,
  minAuthor,
  minAff,
  minNobel,
  minPatent
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));
