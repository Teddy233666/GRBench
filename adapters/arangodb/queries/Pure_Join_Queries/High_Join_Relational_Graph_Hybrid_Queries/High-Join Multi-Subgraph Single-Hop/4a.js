var cursor = db._query(`
  LET startPaper = "Papers/W4211259235"
  LET startKey = PARSE_IDENTIFIER(startPaper).key

  // ---------- g_ref ----------
  LET g_ref = (
    FOR e IN PaperReferences
      FILTER e._from == startPaper

      LET ref = DOCUMENT(e._to)

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

    // ---------- g_ap（LEFT JOIN）----------
    LET authors = (
      FOR e IN Authors_Paper
        FILTER e._to == CONCAT("Papers/", r.paperid)

        LET a = DOCUMENT(e._from)

        FILTER a.h_index > 10

        RETURN a._key
    )

    // ---------- papersources ----------
    LET pss = (
      FOR ps IN papersources
        FILTER ps.paperid == r.ref_paperid
        RETURN ps.sourceid
    )

    // ---------- sources ----------
    LET ss = (
      FOR s IN sources
        FILTER s.sourceid IN pss
        RETURN s.sourceid
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
        FILTER ad.authorid IN authors
        RETURN ad.display_name
    )

    // ---------- LEFT JOIN 展开 ----------
    FOR a IN (LENGTH(authors) > 0 ? authors : [null])
      FOR s IN (LENGTH(ss) > 0 ? ss : [null])
        FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
          FOR ad IN (LENGTH(ads) > 0 ? ads : [null])

            COLLECT AGGREGATE
              minPaper = MIN(r.paperid),
              minAuthor = MIN(a),
              minSource = MIN(s),
              minNobel = MIN(ln),
              minPatent = MIN(ad)

            RETURN {
              minPaper,
              minAuthor,
              minSource,
              minNobel,
              mindisplay_name: minPatent
            }
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));