var cursor = db._query(`
LET start = DOCUMENT("Papers/W2122344208")

LET g_ref = (
  FOR ref IN 1..1 OUTBOUND start PaperReferences
    FILTER ref.citation_count < 150
    RETURN {
      p1: start._key,
      p3: ref._key
    }
)

FOR r IN g_ref

  // ---------- nf（INNER JOIN）----------
  FOR nf IN (
    FOR n IN 1..1 OUTBOUND CONCAT("Papers/", r.p1) link_newsfeed
      RETURN n.newsfeed_id
  )

  // ---------- ln（INNER JOIN）----------
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