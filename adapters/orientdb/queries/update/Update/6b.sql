script sql
LET author_rows = (SELECT FROM grbench_update4_authors_gender);
FOREACH (e IN $author_rows) {
  CREATE VERTEX Authors_Gender SET authorid = $e.authorid, avg_c10 = $e.avg_c10, avg_logc10 = $e.avg_logc10, productivity = $e.productivity, h_index = $e.h_index, display_name = $e.display_name, inference_sources = $e.inference_sources, inference_counts = $e.inference_counts, P_gf = $e.P_gf;
}
LET papers_to_authors_rows = (SELECT FROM grbench_update6_papers_to_authors);
FOREACH (e IN $papers_to_authors_rows) {
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
LET affiliated_with_rows = (SELECT FROM grbench_update6_affiliated_with);
FOREACH (e IN $affiliated_with_rows) {
  LET from_vertex = (SELECT FROM Authors_Gender WHERE authorid = $e.authorid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Authors_Gender' AND target_key = 'authorid' AND target_value = ifnull($e.authorid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Affiliations WHERE institutionid = $e.institution_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Affiliations' AND target_key = 'institutionid' AND target_value = ifnull($e.institution_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE affiliated_with FROM $from_vertex TO $to_vertex SET authorid = $e.authorid, institution_id = $e.institution_id;
}
RETURN $author_rows.size() + $papers_to_authors_rows.size() + $affiliated_with_rows.size();
end
