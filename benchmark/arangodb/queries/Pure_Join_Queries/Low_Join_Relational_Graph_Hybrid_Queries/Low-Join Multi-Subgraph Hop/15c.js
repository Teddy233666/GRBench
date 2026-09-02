var cursor = db._query(`
  LET startPaper = "Papers/W2122344208"
  LET startKey = PARSE_IDENTIFIER(startPaper).key

  // ---------- g_ref ----------
  LET g_ref = (
    FOR e1 IN PaperReferences
      FILTER e1._from == startPaper
      LET v1 = e1._to

      FOR e2 IN PaperReferences
        FILTER e2._from == v1
        LET v2 = e2._to

        FOR e3 IN PaperReferences
          FILTER e3._from == v2

          LET ref = DOCUMENT(e3._to)

          FILTER ref.citation_count < 5

          RETURN {
            p1: startKey,
            p3: ref._key
          }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ p1: startKey, p3: null }]
  )

    // ---------- PaperFields ----------
    LET pfs = (
      FOR e IN PaperFields
        FILTER e._from == CONCAT("Papers/", r.p3)

        LET f = DOCUMENT(e._to)

        RETURN f.fieldid
    )

    // ---------- Newsfeed ----------
    LET nfs = (
      FOR e IN link_newsfeed
        FILTER e._from == CONCAT("Papers/", r.p1)

        LET n = DOCUMENT(e._to)

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
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));