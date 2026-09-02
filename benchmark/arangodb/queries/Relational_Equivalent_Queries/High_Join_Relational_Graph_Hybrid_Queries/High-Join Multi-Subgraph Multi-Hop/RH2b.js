db._query(`
LET startPaper = "Papers/W2122344208"
LET startId = PARSE_IDENTIFIER(startPaper).key

LET data = (
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
        LET refId = PARSE_IDENTIFIER(ref._id).key

        // ---------- Authors (替代 INBOUND) ----------
        LET authors = (
          FOR e IN Authors_Paper
            FILTER e._to == ref._id
            LET a = DOCUMENT(e._from)
            FILTER a.h_index > 30
            RETURN a._key
        )

        // ---------- NSF (替代 OUTBOUND startPaper) ----------
        LET nsfs = (
          FOR e IN Link_NSF
            FILTER e._from == startPaper
            LET n = DOCUMENT(e._to)
            RETURN n.award_id
        )

        // ---------- ps ----------
        LET pss = (
          FOR ps IN papersources
            FILTER ps.paperid == refId
            RETURN ps.sourceid
        )

        // ---------- s ----------
        LET ss = (
          FOR s IN sources
            FILTER s.sourceid IN pss
            RETURN s.sourceid
        )

        // ---------- ln ----------
        LET lns = (
          FOR ln IN link_nobellaureates
            FILTER ln.paperid == startId
            RETURN ln.laureate_id
        )

        // ---------- ad ----------
        LET ads = (
          FOR ad IN author_details
            FILTER ad.authorid IN authors
            RETURN ad.authorid
        )

        // ---------- LEFT JOIN 展开 ----------
        FOR a IN (LENGTH(authors) > 0 ? authors : [null])
          FOR nsf IN (LENGTH(nsfs) > 0 ? nsfs : [null])
            FOR ps IN (LENGTH(pss) > 0 ? pss : [null])
              FOR s IN (LENGTH(ss) > 0 ? ss : [null])
                FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
                  FOR ad IN (LENGTH(ads) > 0 ? ads : [null])

                  RETURN {
                    paperid: startId,
                    authorid: a,
                    nsf_id: nsf,
                    sourceid: s,
                    nobelid: ln,
                    patentid: ad
                  }
)

FOR item IN data
COLLECT AGGREGATE
  minPaper = MIN(item.paperid),
  minAuthor = MIN(item.authorid),
  minnsf = MIN(item.nsf_id),
  minSource = MIN(item.sourceid),
  minNobel = MIN(item.nobelid),
  minPatent = MIN(item.patentid)

RETURN {
  minPaper,
  minAuthor,
  minnsf,
  minSource,
  minNobel,
  minPatent
}`).toArray()