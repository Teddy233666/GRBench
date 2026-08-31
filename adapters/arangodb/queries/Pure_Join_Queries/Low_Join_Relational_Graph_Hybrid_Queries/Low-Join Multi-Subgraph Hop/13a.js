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

          FILTER ref.citation_count < 150

          RETURN {
            paperid: startKey,
            ref_paperid: ref._key
          }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ paperid: startKey, ref_paperid: null }]
  )

    // ---------- g_ap（Authors）----------
    LET aps = (
      FOR e IN Authors_Paper
        FILTER e._to == CONCAT("Papers/", r.paperid)

        LET a = DOCUMENT(e._from)

        FILTER a.h_index > 10

        RETURN a._key
    )

    // ---------- g_cf（Affiliation）----------
    LET cfs = (
      FOR e IN contributed_from
        FILTER e._from == CONCAT("Papers/", r.ref_paperid)

        LET aff = DOCUMENT(e._to)

        FILTER aff.productivity > 1000

        RETURN r.ref_paperid
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
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));