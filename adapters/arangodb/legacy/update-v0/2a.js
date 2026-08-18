db._query(`
FOR e IN grbench_update2_edges
  FILTER e.citing_paperid != null AND e.cited_paperid != null
  INSERT {
    _from: CONCAT("Papers/", e.citing_paperid),
    _to: CONCAT("Papers/", e.cited_paperid)
  } INTO PaperReferences
`);

db._query(`
FOR p1 IN Papers
  FOR p2, r IN OUTBOUND p1 PaperReferences
    FILTER (p1.year >= 2020 AND p1.year <= 2025)
        OR (p2.year >= 2020 AND p2.year <= 2025)
    REMOVE r IN PaperReferences
`, {}, { batchSize: 5000 });