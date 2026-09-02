var cursor = db._query(`
  LET startPaper = "Papers/W4211259235"
  LET start = DOCUMENT(startPaper)

  // ---------- g_ref ----------
  LET g_ref = (
    FOR e IN PaperReferences
      FILTER e._from == startPaper

      LET ref = DOCUMENT(e._to)

      FILTER ref.citation_count < 150

      RETURN {
        p1: start._key,
        p3: ref._key
      }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ p1: start._key, p3: null }]
  )

    // ---------- LEFT JOIN link_newsfeed ----------
    LET nfs = (
      FOR e IN link_newsfeed
        FILTER e._from == CONCAT("Papers/", r.p1)

        LET n = DOCUMENT(e._to)

        RETURN n.newsfeed_id
    )

    // ---------- LEFT JOIN papersources ----------
    LET pss = (
      FOR ps IN papersources
        FILTER ps.paperid == r.p1
        RETURN ps.sourceid
    )

    // ---------- LEFT JOIN sources ----------
    LET ss = (
      FOR s IN sources
        FILTER s.sourceid IN pss
        RETURN s.sourceid
    )

    // ---------- LEFT JOIN Nobel ----------
    LET lns = (
      FOR ln IN link_nobellaureates
        FILTER ln.paperid == r.p1
        RETURN ln.laureate_id
    )

    // ---------- LEFT JOIN patents ----------
    LET lps = (
      FOR lp IN link_patents
        FILTER lp.paperid == r.p1
        RETURN lp.patent
    )

    // ---------- 模拟 SQL LEFT JOIN 展开 ----------
    FOR nf IN (LENGTH(nfs) > 0 ? nfs : [null])
      FOR s IN (LENGTH(ss) > 0 ? ss : [null])
        FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
          FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

            COLLECT AGGREGATE
              minPaper = MIN(r.p3),
              minNewsfeed = MIN(nf),
              minSource = MIN(s),
              minNobel = MIN(ln),
              minPatent = MIN(lp)

            RETURN {
              minPaper,
              newsfeed: minNewsfeed,
              minSource,
              minNobel,
              minPatent
            }
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));