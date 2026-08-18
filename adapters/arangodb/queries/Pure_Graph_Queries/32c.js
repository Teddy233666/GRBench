var cursor = db._query(`
LET paths = (
  FOR p5 IN 1..1 OUTBOUND "Papers/W4235901390" PaperReferences
    FOR p6 IN 1..1 OUTBOUND p5 PaperReferences
      FILTER p6.citation_count < 5
      FOR p3 IN 1..1 OUTBOUND p6 PaperReferences
        RETURN { p1: "W4235901390", p3: p3._key }
)

FOR path IN paths
  LET authors = (
    FOR a IN 1..1 INBOUND CONCAT("Papers/", path.p1) Authors_Paper
      RETURN a._key
  )
  LET newsfeeds = (
    FOR n IN 1..1 OUTBOUND CONCAT("Papers/", path.p1) link_newsfeed
      RETURN n.newsfeed_id
  )
  FOR author IN (LENGTH(authors) > 0 ? authors : [null])
    FOR newsfeed IN (LENGTH(newsfeeds) > 0 ? newsfeeds : [null])
      COLLECT AGGREGATE
        min_ref_paperid = MIN(path.p3),
        min_author = MIN(author),
        min_newsfeed = MIN(newsfeed)
      RETURN {
        min_ref_paperid,
        author: min_author,
        newsfeed: min_newsfeed
      }
`)
var result = cursor.toArray();
print(JSON.stringify(result));
