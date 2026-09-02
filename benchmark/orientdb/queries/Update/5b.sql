script sql
LET rows = (SELECT FROM grbench_update5_papers_to_authors);
FOREACH (e IN $rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Authors_Gender WHERE authorid = $e.authorid LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Authors_Gender' AND target_key = 'authorid' AND target_value = ifnull($e.authorid, '') LIMIT 1);
  }
  LET created = CREATE EDGE Papers_to_Authors FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, authorid = $e.authorid;
}
RETURN $rows.size();
end
