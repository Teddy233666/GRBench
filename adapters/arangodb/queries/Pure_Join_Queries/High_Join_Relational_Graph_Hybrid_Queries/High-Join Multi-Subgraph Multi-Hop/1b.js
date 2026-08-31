db._query(`
LET startPaper = "Papers/W2122344208"
LET startId = PARSE_IDENTIFIER(startPaper).key

FOR r1 IN PaperReferences
  FILTER r1._from == startPaper

  FOR p1 IN Papers
    FILTER p1._id == r1._to

    FOR r2 IN PaperReferences
      FILTER r2._from == p1._id

      FOR p2 IN Papers
        FILTER p2._id == r2._to

        FOR r3 IN PaperReferences
          FILTER r3._from == p2._id

          FOR ref IN Papers
            FILTER ref._id == r3._to
            FILTER ref.citation_count < 80

            LET refId = PARSE_IDENTIFIER(ref._id).key

            // ---------- authors ----------
            LET authors = (
              FOR a IN 1..1 INBOUND startPaper Authors_Paper
                FILTER a.h_index > 30
                RETURN a._key
            )

            // ---------- aff existence ----------
            LET hasAff = LENGTH(
              FOR aff IN 1..1 OUTBOUND ref contributed_from
                FILTER aff.productivity > 5000
                LIMIT 1
                RETURN 1
            ) > 0

            // ---------- paper sources ----------
            LET pss = (
              FOR ps IN papersources
                FILTER ps.paperid == refId
                RETURN ps.sourceid
            )

            LET ss = (
              FOR s IN sources
                FILTER s.sourceid IN pss
                RETURN s.sourceid
            )

            // ---------- nobel links ----------
            LET lns = (
              FOR ln IN link_nobellaureates
                FILTER ln.paperid == startId
                RETURN ln.laureate_id
            )

            // ---------- author details ----------
            LET ads = (
              FOR ad IN author_details
                FILTER ad.authorid IN authors
                RETURN ad.authorid
            )

            // ---------- LEFT JOIN 展开 ----------
            FOR a IN (LENGTH(authors) > 0 ? authors : [null])
              FOR affPaper IN (hasAff ? [refId] : [null])
                FOR ps IN (LENGTH(pss) > 0 ? pss : [null])
                  FOR s IN (LENGTH(ss) > 0 ? ss : [null])
                    FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
                      FOR ad IN (LENGTH(ads) > 0 ? ads : [null])

                        COLLECT AGGREGATE
                          minPaper = MIN(startId),
                          minAuthor = MIN(a),
                          minAff = MIN(affPaper),
                          minSource = MIN(s),
                          minNobel = MIN(ln),
                          minPatent = MIN(ad)

                        RETURN {
                          minPaper,
                          minAuthor,
                          minAff,
                          minSource,
                          minNobel,
                          minPatent
                        }
`)