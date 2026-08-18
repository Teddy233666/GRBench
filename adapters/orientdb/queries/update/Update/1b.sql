script sql
LET paper_rows = (SELECT FROM grbench_update1_papers);
FOREACH (e IN $paper_rows) {
  CREATE VERTEX Papers SET paperid = $e.paperid, doi = $e.doi, year = $e.year, date = $e.date, doctype = $e.doctype, cited_by_count = $e.cited_by_count, is_retracted = $e.is_retracted, reference_count = $e.reference_count, citation_count = $e.citation_count, C3 = $e.C3, C5 = $e.C5, C10 = $e.C10, disruption = $e.disruption, Atyp_Median_Z = $e.Atyp_Median_Z, Atyp_10pct_Z = $e.Atyp_10pct_Z, Atyp_Pairs = $e.Atyp_Pairs, WSB_mu = $e.WSB_mu, WSB_sigma = $e.WSB_sigma, WSB_Cinf = $e.WSB_Cinf, SB_B = $e.SB_B, SB_T = $e.SB_T, team_size = $e.team_size, institution_count = $e.institution_count, patent_count = $e.patent_count, newsfeed_count = $e.newsfeed_count, nct_count = $e.nct_count, nih_count = $e.nih_count, nsf_count = $e.nsf_count;
}
LET paperreference_rows = (SELECT FROM grbench_update3_paperreferences);
FOREACH (e IN $paperreference_rows) {
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
LET papers_to_authors_rows = (SELECT FROM grbench_update1_papers_to_authors);
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
LET authors_paper_rows = (SELECT FROM grbench_update3_authors_paper);
FOREACH (e IN $authors_paper_rows) {
  LET from_vertex = (SELECT FROM Authors_Gender WHERE authorid = $e.authorid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Authors_Gender' AND target_key = 'authorid' AND target_value = ifnull($e.authorid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET created = CREATE EDGE Authors_Paper FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, authorid = $e.authorid;
}
LET contributed_from_rows = (SELECT FROM grbench_update3_contributed_from);
FOREACH (e IN $contributed_from_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Affiliations WHERE institutionid = $e.institution_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Affiliations' AND target_key = 'institutionid' AND target_value = ifnull($e.institution_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE contributed_from FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, institution_id = $e.institution_id, authorid = $e.authorid;
}
LET paperfield_rows = (SELECT FROM grbench_update3_paperfields);
FOREACH (e IN $paperfield_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Fields WHERE fieldid = $e.fieldid LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Fields' AND target_key = 'fieldid' AND target_value = ifnull($e.fieldid, '') LIMIT 1);
  }
  LET created = CREATE EDGE PaperFields FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, fieldid = $e.fieldid, score_openalex = $e.score_openalex;
}
LET link_nsf_rows = (SELECT FROM grbench_update3_link_nsf);
FOREACH (e IN $link_nsf_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM NSF_Metadata WHERE award_id = $e.award_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'NSF_Metadata' AND target_key = 'award_id' AND target_value = ifnull($e.award_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE Link_NSF FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, award_id = $e.award_id;
}
LET link_nih_rows = (SELECT FROM grbench_update3_link_nih);
FOREACH (e IN $link_nih_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM NIH_Metadata WHERE award_id = $e.award_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'NIH_Metadata' AND target_key = 'award_id' AND target_value = ifnull($e.award_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE Link_NIH FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, award_id = $e.award_id;
}
LET link_clinicaltrials_rows = (SELECT FROM grbench_update3_link_clinicaltrials);
FOREACH (e IN $link_clinicaltrials_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM clinicaltrials_metadata WHERE nct_id = $e.nct_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'clinicaltrials_metadata' AND target_key = 'nct_id' AND target_value = ifnull($e.nct_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE Link_ClinicalTrials FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, nct_id = $e.nct_id;
}
LET link_newsfeed_rows = (SELECT FROM grbench_update3_link_newsfeed);
FOREACH (e IN $link_newsfeed_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Newsfeed_Metadata WHERE newsfeed_id = $e.newsfeed_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Newsfeed_Metadata' AND target_key = 'newsfeed_id' AND target_value = ifnull($e.newsfeed_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE link_newsfeed FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, newsfeed_id = $e.newsfeed_id;
}
LET link_twitter_rows = (SELECT FROM grbench_update3_link_twitter);
FOREACH (e IN $link_twitter_rows) {
  LET from_vertex = (SELECT FROM Papers WHERE paperid = $e.paperid LIMIT 1);
  IF ($from_vertex.size() = 0) {
    LET from_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Papers' AND target_key = 'paperid' AND target_value = ifnull($e.paperid, '') LIMIT 1);
  }
  LET to_vertex = (SELECT FROM Twitter_Metadata WHERE tweet_id = $e.tweet_id LIMIT 1);
  IF ($to_vertex.size() = 0) {
    LET to_vertex = (SELECT FROM _MissingEndpoint WHERE target_class = 'Twitter_Metadata' AND target_key = 'tweet_id' AND target_value = ifnull($e.tweet_id, '') LIMIT 1);
  }
  LET created = CREATE EDGE link_twitter FROM $from_vertex TO $to_vertex SET paperid = $e.paperid, tweet_id = $e.tweet_id;
}
RETURN $paper_rows.size() + $paperreference_rows.size() + $papers_to_authors_rows.size() + $authors_paper_rows.size() + $contributed_from_rows.size() + $paperfield_rows.size() + $link_nsf_rows.size() + $link_nih_rows.size() + $link_clinicaltrials_rows.size() + $link_newsfeed_rows.size() + $link_twitter_rows.size();
end
