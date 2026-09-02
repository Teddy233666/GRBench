db._query(`
FOR p4 IN Papers
  FILTER STARTS_WITH(p4._key, "W423590139")
  FILTER p4.citation_count =1

  // ===== INNER JOIN PaperReferences =====
  FOR r1 IN PaperReferences
    FILTER r1.citing_paperid == p4._key

    // ===== INNER JOIN ref =====
    FOR ref IN Papers
      FILTER ref._key == r1.cited_paperid

      // ===== LEFT JOIN NSF =====
      LET ln = FIRST(
        FOR ln IN Link_NSF
          FILTER ln.paperid == p4._key
          RETURN ln.paperid
      )

      LET n_nsf = FIRST(
        FOR n IN NSF_Metadata
          FILTER n.paperid == ln
          RETURN n.paperid
      )

      // ===== 聚合 =====
      COLLECT AGGREGATE
        min_ref = MIN(ref._key),
        minNSF = MIN(ln),
        minNSFMeta = MIN(n_nsf)

      RETURN {
        min_ref,
        minNSF,
        minNSFMeta
      }
`).toArray()