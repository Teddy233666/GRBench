db._query(`
FOR p IN Papers
  FILTER p._key == "W2122344208"

  // ===== INNER JOIN（路径必须存在）=====
  FOR r1 IN PaperReferences
    FILTER r1._from == p._id

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
              FILTER ref.citation_count < 5

              // link_patents（单值）
              LET lp = FIRST(
                FOR lp IN link_patents
                  FILTER lp.paperid == p._key
                  RETURN lp._key
              )

              // ===== 聚合 =====
              COLLECT AGGREGATE
                min_ref = MIN(p._key),
                minPatent = MIN(lp)

              RETURN {
                min_ref,
                minPatent
              }
`).toArray()