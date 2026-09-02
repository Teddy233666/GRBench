var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 150
        RETURN {
          p1: "W2122344208",
          p3: ref._key
        }
)

FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ p1: "W2122344208", p3: null }])

  // ---------- PaperFields ----------
  LET pfs = (
    FOR f IN 1..1 OUTBOUND CONCAT("Papers/", r.p3) PaperFields
      RETURN f.fieldid
  )

  // ---------- Newsfeed ----------
  LET nfs = (
    FOR n IN 1..1 OUTBOUND CONCAT("Papers/", r.p1) link_newsfeed
      RETURN n.newsfeed_id
  )

  // ---------- Nobel ----------
  LET lns = (
    FOR ln IN link_nobellaureates
      FILTER ln.paperid == r.p1
      RETURN ln.laureate_id
  )

  // ---------- LEFT JOIN 展开 ----------
  FOR pf IN (LENGTH(pfs) > 0 ? pfs : [null])
    FOR nf IN (LENGTH(nfs) > 0 ? nfs : [null])
      FOR ln IN (LENGTH(lns) > 0 ? lns : [null])

        COLLECT AGGREGATE
          minPaper = MIN(r.p3),
          minField = MIN(pf),
          minNewsfeed = MIN(nf),
          minNobel = MIN(ln)

RETURN {
  minPaper,
  fieldid: minField,
  newsfeed: minNewsfeed,
  minNobel
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));