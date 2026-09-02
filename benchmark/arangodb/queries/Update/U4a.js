// 删除 Papers_to_Authors（备份 cohort）；需先运行 backup.js
db._query(`
FOR e IN grbench_update6_papers_to_authors
  FILTER e.paperid != null AND e.authorid != null
  COLLECT paperid = e.paperid, authorid = e.authorid
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("Authors_Gender/", authorid)
  FOR r IN Authors_Paper
    FILTER r._from == toId AND r._to == fromId
    REMOVE r IN Authors_Paper
`, {}, { batchSize: 5000 });
