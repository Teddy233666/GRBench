var cursor = db._query(`
LET g_ref = (
  FOR p IN Papers
    FILTER STARTS_WITH(p.paperid, "W423590139")
      AND p.citation_count <= 1
    FOR n IN 1..1 OUTBOUND p Link_NSF
      RETURN { paperid: p._key }
)

FOR r IN (LENGTH(g_ref) > 0 ? g_ref : [{ paperid: null }])

  // ---------- papersources ----------
  LET pss = (
    FOR ps IN papersources
      FILTER ps.paperid == r.paperid
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

  // ---------- h0paperids ----------
  LET lps = (
    FOR lp IN hit_papers_level0
      FILTER lp.paperid == r.paperid
      RETURN lp.paperid
  )


  // ---------- LEFT JOIN 展开 ----------
  FOR s IN (LENGTH(ss) > 0 ? ss : [null])
    FOR ln IN (LENGTH(lns) > 0 ? lns : [null])
      FOR lp IN (LENGTH(lps) > 0 ? lps : [null])

        COLLECT AGGREGATE
          cited_paperid = MIN(r.paperid),
          minSource = MIN(s),
          minNobel = MIN(ln),
          minh0paperid = MIN(lp)

RETURN {
  cited_paperid,
  minSource,
  minNobel,
  minh0paperid
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));