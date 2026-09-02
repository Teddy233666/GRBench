script sql
LET rows = (SELECT paperid, authorid FROM grbench_update5_papers_to_authors);
FOREACH (e IN $rows) {
  DELETE EDGE Papers_to_Authors
  WHERE paperid = $e.paperid
    AND authorid = $e.authorid;
}
RETURN $rows.size();
end
