var cursor = db._query(`
  LET startPaper = "Papers/W2122344208"
  LET start = DOCUMENT(startPaper)

  // ---------- g_ref ----------
  LET g_ref = (
    FOR e IN PaperReferences
      FILTER e._from == start._id

      LET ref = DOCUMENT(e._to)

      FILTER ref.citation_count < 80

      RETURN {
        paper: start,
        ref: ref
      }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ paper: start, ref: null }]
  )

    // =====================
    // Authors_Paper (g_ap)
    // =====================
    LET aps = (
      FOR e IN Authors_Paper
        FILTER e._to == r.paper._id

        LET a = DOCUMENT(e._from)

        FILTER a.h_index > 30

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
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));