var cursor = db._query(`
  // ---------- g_ref ----------
  LET g_ref = (
    FOR p IN Papers
      FILTER STARTS_WITH(p._key, "W423590139")
        AND p.citation_count == 1

      FOR e IN Link_NIH
        FILTER e._from == p._id

        RETURN {
          paperid: p._key
        }
  )

  FOR r IN (
    LENGTH(g_ref) > 0
      ? g_ref
      : [{ paperid: null }]
  )

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
            cited_paperid = MIN(r.paperid),
            minSource = MIN(s),
            minNobel = MIN(ln),
            minPatent = MIN(lp)

          RETURN {
            cited_paperid,
            minSource,
            minNobel,
            minPatent
          }
`);

var result = cursor.toArray();

print(JSON.stringify(result, null, 2));