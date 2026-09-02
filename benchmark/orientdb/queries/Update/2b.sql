script sql
LET rows = (SELECT FROM grbench_update2_edges);
FOREACH (e IN $rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.citing_paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.citing_paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Papers WHERE paperid = $e.cited_paperid LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.cited_paperid, '') LIMIT 1);
  }
  LET created = CREATE EDGE PaperReferences FROM $from_vertex TO $to_vertex SET citing_paperid = $e.citing_paperid, cited_paperid = $e.cited_paperid, year = $e.year, ref_year = $e.ref_year, year_diff = $e.year_diff;
}
RETURN $rows.size();
end
