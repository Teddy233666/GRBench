// Relational equivalent of S4c; edge-collection expansion, not AQL shortest-path syntax.
db._query(`
LET candidates = (
  FOR v, e, p IN 0..1000000000 OUTBOUND "Affiliations/I4210136388" affl_assoc_affl
    OPTIONS { order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }
    FILTER v._key == 'I4210088668'
    RETURN v._key
)
RETURN MIN(candidates) AS inst_asia_institutionid
`)
