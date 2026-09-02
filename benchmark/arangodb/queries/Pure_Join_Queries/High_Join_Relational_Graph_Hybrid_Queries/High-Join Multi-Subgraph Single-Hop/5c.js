var cursor = db._query(`
  LET startPaper = "Papers/W4211259235"
  LET startKey = PARSE_IDENTIFIER(startPaper).key

  // ---------- g_ref ----------
  LET g_ref = (
    FOR e IN PaperReferences
      FILTER e._from == startPaper

      LET ref = DOCUMENT(e._to)

      FILTER ref.citation_count < 5

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

    // ---------- NSF（LEFT JOIN）----------
    LET nsfs = (
      FOR e IN Link_NSF
        FILTER e._from == CONCAT("Papers/", r.paperid)

        LET aff = DOCUMENT(e._to)

        RETURN aff.award_id
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

    // ---------- patents ----------
    LET lps = (
      FOR lp IN link_patents
        FILTER lp.paperid == r.ref_paperid
        RETURN lp.patent
    )

    // ---------- LEFT JOIN 展开 ----------
    FOR nsf IN (LENGTH(nsfs) > 0 ? nsfs : [null])
      FOR s IN (LENGTH(ss) > 0 ? ss : [null])
        FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
          FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

            COLLECT AGGREGATE
              minPaper = MIN(r.paperid),
              minAff = MIN(nsf),
              minSource = MIN(s),
              minNobel = MIN(ln),
              minPatent = MIN(lp)

            RETURN {
              minPaper,
              award_id: minAff,
              minSource,
              minNobel,
              minPatent
            }
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));