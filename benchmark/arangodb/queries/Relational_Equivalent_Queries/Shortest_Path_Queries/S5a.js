// Relational equivalent of S5a; edge-collection expansion over PaperReferences.
print(JSON.stringify(db._query(`
LET start = "Papers/W4211259235"
LET candidates = (
  FOR v, e, p IN 0..1 OUTBOUND start PaperReferences
    OPTIONS { order: "bfs", uniqueVertices: "global", uniqueEdges: "path" }
    FILTER v.citation_count < 150
    RETURN v._key
)
RETURN MIN(candidates)
`).toArray()));
