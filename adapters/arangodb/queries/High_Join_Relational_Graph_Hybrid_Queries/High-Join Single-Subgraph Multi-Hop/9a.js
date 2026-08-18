var cursor = db._query(`
LET g_ref = (
  FOR v1 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR v2 IN 1..1 OUTBOUND v1 PaperReferences
      FOR ref IN 1..1 OUTBOUND v2 PaperReferences
        FILTER ref.citation_count < 150
        RETURN {
          paperid: "W2122344208",
          cited_paperid: ref._key
        }
)

FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: "W2122344208", cited_paperid: null }])

  // ---------- level0 ----------
  LET h0s = (
    FOR hp IN normalized_citations_level0
      FILTER hp.paperid == r.paperid
      RETURN hp.fieldid
  )

  // ---------- level1 ----------
  LET h1s = (
    FOR h1 IN normalized_citations_level1
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
  minPaper,
  fieldid0: minH0,
  fieldid1: minH1,
  minNobel,
  minPatent
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));