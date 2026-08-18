var cursor =db._query(`
LET startPaper = "Papers/W2122344208"
LET startId = PARSE_IDENTIFIER(startPaper).key

FOR v1 IN 1..1 OUTBOUND startPaper PaperReferences
  FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
    FOR ref IN 1..1 OUTBOUND v2 PaperReferences
      FILTER ref.citation_count < 150

      LET refId = PARSE_IDENTIFIER(ref._id).key

      // ---------- g_ap (LEFT JOIN) ----------
      LET authors = (
        FOR a IN 1..1 INBOUND startPaper Authors_Paper
          FILTER a.h_index > 10
          RETURN a._key
      )

      // ---------- g_cf (LEFT JOIN, 关键！！！) ----------
      LET hasAff = LENGTH(
        FOR aff IN 1..1 OUTBOUND ref contributed_from
          FILTER aff.productivity > 1000
          LIMIT 1
          RETURN 1
      ) > 0

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
var result = cursor.toArray();
print(JSON.stringify(result));