db._query(`
FOR e IN grbench_update6_papers_to_authors
  FILTER e.paperid != null AND e.authorid != null
  INSERT {
    _from: CONCAT("Authors_Gender/", e.authorid),
    _to: CONCAT("Papers/", e.paperid)
  } INTO Authors_Paper
`);
