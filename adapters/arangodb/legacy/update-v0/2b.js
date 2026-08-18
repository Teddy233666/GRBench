db._query(`
FOR e IN grbench_update2_edges
  COLLECT citing = e.citing_paperid, cited = e.cited_paperid
  LET fromId = CONCAT("Papers/", citing)
  LET toId   = CONCAT("Papers/", cited)

  FOR r IN PaperReferences
    FILTER r._from == fromId
      AND r._to   == toId
    REMOVE r IN PaperReferences
`, {}, { batchSize: 5000});
