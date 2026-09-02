db._query(`
LET start = "Papers/W4211259235"
LET candidates = UNION_DISTINCT(
  (
    FOR paper IN Papers
      FILTER paper._id == start AND paper.citation_count < 80
      RETURN paper._key
  ),
  (
    FOR ref IN 1..1 OUTBOUND start PaperReferences
      FILTER ref.citation_count < 80
      RETURN ref._key
  )
)
RETURN MIN(candidates)
`)
