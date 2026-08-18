db._query(`
LET start = "Affiliations/I4210136388"
LET candidates = (
  FOR end IN Affiliations
    FILTER end.productivity > 48000
    LET pathVertices = (
      FOR vertex IN OUTBOUND SHORTEST_PATH start TO end._id affl_assoc_affl
        RETURN 1
    )
    FILTER LENGTH(pathVertices) > 1
    RETURN end._key
)
RETURN MIN(candidates)
`)
