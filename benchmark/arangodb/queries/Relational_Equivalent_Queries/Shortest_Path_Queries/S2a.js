// Relational equivalent of S2a; edge-collection expansion, not AQL shortest-path syntax.
db._query(`
LET candidates = (
  FOR v, e, p IN 1..3 OUTBOUND "Affiliations/I4210136388" affl_assoc_affl
    OPTIONS { order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }
    FILTER v.productivity > 8000
    RETURN v._key
)
RETURN MIN(candidates) AS inst_for_institutionid
`)
