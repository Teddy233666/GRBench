var cursor = db._query(`
  LET startPaper = "Papers/W4211259235"
  LET start = DOCUMENT(startPaper)

  // ---------- g_ref ----------
  LET g_ref = (
    FOR e IN PaperReferences
      FILTER e._from == start._id

      LET ref = DOCUMENT(e._to)

      FILTER ref.citation_count < 5

      RETURN {
        paperid: start._key,
        ref_paperid: ref._key
      }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ paperid: start._key, ref_paperid: null }]
  )

    // ---------- NSF ----------
    LET nsfs = (
      FOR e IN Link_NSF
        FILTER e._from == CONCAT("Papers/", r.paperid)

        LET n = DOCUMENT(e._to)

        RETURN n.award_id
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
      FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
        FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

          COLLECT AGGREGATE
            minPaper = MIN(r.paperid),
            minNSF = MIN(nsf),
            minNobel = MIN(ln),
            minPatent = MIN(lp)

          RETURN {
            minPaper,
            award_id: minNSF,
            minNobel,
            minPatent
          }
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));