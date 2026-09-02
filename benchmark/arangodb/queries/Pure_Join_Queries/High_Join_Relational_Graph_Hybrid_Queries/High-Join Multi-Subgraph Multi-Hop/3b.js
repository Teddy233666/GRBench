 var cursor = db._query(`
    LET startPaper = "Papers/W2122344208"
    LET startKey = PARSE_IDENTIFIER(startPaper).key

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

            FILTER ref.citation_count < 80

            RETURN {
              p1: startKey,
              p3: PARSE_IDENTIFIER(ref._id).key
            }
    )

    FOR r IN g_ref

      // ---------- PaperFields (LEFT JOIN p3) ----------
      LET pfs = (
        FOR e IN PaperFields
          FILTER e._from == CONCAT("Papers/", r.p3)
          LET f = DOCUMENT(e._to)
          RETURN f._key
      )

      // ---------- Newsfeed (LEFT JOIN p1) ----------
      LET nfs = (
        FOR e IN link_newsfeed
          FILTER e._from == CONCAT("Papers/", r.p1)
          LET n = DOCUMENT(e._to)
          RETURN n.newsfeed_id
      )

      // ---------- papersources ----------
      LET pss = (
        FOR ps IN papersources
          FILTER ps.paperid == r.p1
          RETURN ps.sourceid
      )

      LET ss = (
        FOR s IN sources
          FILTER s.sourceid IN pss
          RETURN s.sourceid
      )

      // ---------- Nobel ----------
      LET lns = (
        FOR ln IN link_nobellaureates
          FILTER ln.paperid == r.p1
          RETURN ln.laureate_id
      )

      // ---------- patents ----------
      LET lps = (
        FOR lp IN link_patents
          FILTER lp.paperid == r.p1
          RETURN lp.patent
      )

      // ---------- LEFT JOIN EXPAND ----------
      FOR pf IN (LENGTH(pfs) > 0 ? pfs : [null])
        FOR nf IN (LENGTH(nfs) > 0 ? nfs : [null])
          FOR ps IN (LENGTH(pss) > 0 ? pss : [null])
            FOR s IN (LENGTH(ss) > 0 ? ss : [null])
              FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
                FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

                  COLLECT AGGREGATE
                    minPaper = MIN(r.p3),
                    minField = MIN(pf),
                    minNews = MIN(nf),
                    minSource = MIN(s),
                    minNobel = MIN(ln),
                    minPatent = MIN(lp)

                  RETURN {
                    minPaper,
                    fieldid: minField,
                    newsfeed: minNews,
                    minSource,
                    minNobel,
                    minPatent
                  }
  `);

  var result = cursor.toArray();
  print(JSON.stringify(result, null, 2));
