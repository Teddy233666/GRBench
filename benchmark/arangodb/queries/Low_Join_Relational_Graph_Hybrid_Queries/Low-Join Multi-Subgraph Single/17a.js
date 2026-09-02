var cursor =db._query(`
LET start = DOCUMENT("Papers/W4211259235")

LET g_ref = (
  FOR ref IN 1..1 OUTBOUND start PaperReferences
    FILTER ref.citation_count < 150
    RETURN {
      paperid: start._key,
      ref_paperid: ref._key
    }
)

FOR r IN (LENGTH(g_ref) > 0
          ? g_ref
          : [{ paperid: start._key, ref_paperid: null }])

  // ---------- NSF ----------
  LET nsfs = (
    FOR n IN 1..1 OUTBOUND CONCAT("Papers/", r.paperid) Link_NSF
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
`)
var result = cursor.toArray();
print(JSON.stringify(result));