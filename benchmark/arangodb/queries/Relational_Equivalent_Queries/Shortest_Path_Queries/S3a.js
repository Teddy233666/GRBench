// Relational equivalent of S3a; collection-level expansion and join.
db._query(`
LET endpoints = (
  FOR v, e, p IN 1..4 OUTBOUND "Affiliations/I4210136388" affl_assoc_affl
    OPTIONS { order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }
    FILTER v.productivity > 8000
    RETURN v._key
)
LET candidates = (
  FOR cf IN contributed_from
    FILTER PARSE_IDENTIFIER(cf._to).key IN endpoints
    RETURN PARSE_IDENTIFIER(cf._to).key
)
RETURN MIN(candidates)
`)
