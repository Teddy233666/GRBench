db._query(`
LET start = "Affiliations/I4210136388"
LET endpoints = (
  FOR end IN Affiliations
    FILTER end._key == "I4210088668"
    LET pathVertices = (
      FOR vertex IN OUTBOUND SHORTEST_PATH start TO end._id affl_assoc_affl
        RETURN 1
    )
    FILTER LENGTH(pathVertices) >= 2 AND LENGTH(pathVertices) <= 5
    RETURN end
)
LET joinedEndpoints = (
  FOR end IN endpoints
    LET hasPaper = LENGTH(
      FOR paper IN INBOUND end._id contributed_from
        LIMIT 1
        RETURN 1
    ) > 0
    FILTER hasPaper
    RETURN end._key
)
RETURN MIN(joinedEndpoints)
`)
