var cursor = db._query(`
LET start = DOCUMENT("Papers/W2122344208")

LET g_ref = (
  FOR ref IN 1..1 OUTBOUND start PaperReferences
    FILTER ref.citation_count < 80
    RETURN {
      p1: start._key,
      p3: ref._key
    }
)

LET hasRows = LENGTH(g_ref) > 0
LET minPaper = MIN(g_ref[*].p3)
LET minNewsfeed = hasRows ? FIRST(
  FOR n IN 1..1 OUTBOUND start link_newsfeed
    COLLECT AGGREGATE value = MIN(n.newsfeed_id)
    RETURN value
) : null
LET minNobel = hasRows ? FIRST(
  FOR l IN link_nobellaureates
    FILTER l.paperid == start._key
    COLLECT AGGREGATE value = MIN(l.laureate_id)
    RETURN value
) : null

RETURN {
  minPaper,
  newsfeed: minNewsfeed,
  minNobel
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));
