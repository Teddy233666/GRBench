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
            cited_paperid: ref._key
          }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ paperid: startKey, cited_paperid: null }]
  )

    // ---------- h0 ----------
    LET h0s = (
      FOR h0 IN hit_papers_level0
        FILTER h0.paperid == r.paperid
        RETURN h0.fieldid
    )

    // ---------- h1 ----------
    LET h1s = (
      FOR h1 IN hit_papers_level1
        FILTER h1.paperid == r.paperid
        RETURN h1.fieldid
    )

    // ---------- Nobel ----------
    LET lns = (
      FOR ln IN link_nobellaureates
        FILTER ln.paperid == r.cited_paperid
        RETURN ln.laureate_id
    )

    // ---------- patents ----------
    LET lps = (
      FOR lp IN link_patents
        FILTER lp.paperid == r.cited_paperid
        RETURN lp.patent
    )

    // ---------- LEFT JOIN 展开 ----------
    FOR h0 IN (LENGTH(h0s) > 0 ? h0s : [null])
      FOR h1 IN (LENGTH(h1s) > 0 ? h1s : [null])
        FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
          FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

            COLLECT AGGREGATE
              minPaper = MIN(r.paperid),
              minH0 = MIN(h0),
              minH1 = MIN(h1),
              minNobel = MIN(ln),
              minPatent = MIN(lp)

            RETURN {
              cited_paperid: minPaper,
              fieldid0: minH0,
              fieldid1: minH1,
              minNobel,
              minPatent
            }
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));