// 删除 Authors 及相关边；需先运行 backup.js
var BATCH = { batchSize: 5000 };

db._query(`
FOR e IN grbench_update6_papers_to_authors
  FILTER e.authorid != null AND e.paperid != null
  COLLECT authorid = e.authorid, paperid = e.paperid
  LET fromId = CONCAT("Authors_Gender/", authorid)
  LET toId   = CONCAT("Papers/", paperid)
  FOR r IN Authors_Paper
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN Authors_Paper
`, {}, BATCH);

db._query(`
FOR e IN grbench_update6_affiliated_with
  FILTER e.authorid != null AND e.institutionid != null
  COLLECT authorid = e.authorid, institutionid = e.institutionid, author_position = e.author_position
  LET fromId = CONCAT("Authors_Gender/", authorid)
  LET toId   = CONCAT("Affiliations/", institutionid)
  FOR r IN affiliated_with
    FILTER r._from == fromId AND r._to == toId
    FILTER author_position == null OR r.author_position == author_position
    REMOVE r IN affiliated_with
`, {}, BATCH);
