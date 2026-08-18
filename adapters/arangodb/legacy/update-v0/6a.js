db._query(`
FOR e IN grbench_update6_papers_to_authors
  FILTER e.paperid != null AND e.authorid != null
  INSERT {
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("Authors_Gender/", e.authorid)
  } INTO Papers_to_Authors
`);

db._query(`
FOR e IN grbench_update6_affiliated_with
  FILTER e.authorid != null AND e.institutionid != null
  INSERT MERGE({
    _from: CONCAT("Authors_Gender/", e.authorid),
    _to: CONCAT("Affiliations/", e.institutionid)
  }, e.author_position != null ? { author_position: e.author_position } : {}) INTO affiliated_with
`);
