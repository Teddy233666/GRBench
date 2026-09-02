var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 150
        RETURN {
          p1: "W2122344208",
          p3: PARSE_IDENTIFIER(ref._id).key
        }
)

FOR r IN g_ref

  // ---------- PaperFields (LEFT JOIN on p3) ----------
  LET pfs = (
    FOR f IN 1..1 OUTBOUND CONCAT("Papers/", r.p3) PaperFields
      RETURN f._key
  )

  // ---------- Newsfeed (LEFT JOIN on p1) ----------
  LET nfs = (
    FOR n IN 1..1 OUTBOUND CONCAT("Papers/", r.p1) link_newsfeed
      RETURN n.newsfeed_id
  )

  // ---------- papersources (LEFT JOIN on p1) ----------
  LET pss = (
    FOR ps IN papersources
      FILTER ps.paperid == r.p1
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
      FILTER ln.paperid == r.p1
      RETURN ln.laureate_id
  )

  // ---------- patents ----------
  LET lps = (
    FOR lp IN link_patents
      FILTER lp.paperid == r.p1
      RETURN lp.patent
  )

  // ---------- LEFT JOIN 展开 ----------
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
`)
var result = cursor.toArray();
print(JSON.stringify(result));