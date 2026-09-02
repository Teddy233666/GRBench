var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 5
        RETURN {
          paperid: "W2122344208",
          cited_paperid: ref._key
        }
)

FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: "W2122344208", cited_paperid: null }])

  // ---------- papersources ----------
  LET pss = (
    FOR ps IN papersources
      FILTER ps.paperid == r.cited_paperid
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
      FILTER lp.paperid == r.paperid
      RETURN lp.patent
  )

  // ---------- LEFT JOIN 展开 ----------
  FOR s IN (LENGTH(ss) > 0 ? ss : [null])
    FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
      FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

        COLLECT AGGREGATE
          minPaper = MIN(r.paperid),
          minSource = MIN(s),
          minNobel = MIN(ln),
          minPatent = MIN(lp)

RETURN {
  cited_paperid: minPaper,
  minSource,
  minNobel,
  minPatent
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));