db._query(`
FOR e IN grbench_update3_paperreferences
  FILTER e.citing_paperid != null AND e.cited_paperid != null
  INSERT {
    _from: CONCAT("Papers/", e.citing_paperid),
    _to: CONCAT("Papers/", e.cited_paperid)
  } INTO PaperReferences
`);

db._query(`
FOR e IN grbench_update3_papers_to_authors
  FILTER e.paperid != null AND e.authorid != null
  INSERT {
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("Authors_Gender/", e.authorid)
  } INTO Papers_to_Authors
`);

db._query(`
FOR e IN grbench_update3_papers_to_authors
  FILTER e.authorid != null AND e.paperid != null
  INSERT {
    _from: CONCAT("Authors_Gender/", e.authorid),
    _to: CONCAT("Papers/", e.paperid)
  } INTO Authors_Paper
`);

db._query(`
FOR e IN grbench_update3_contributed_from
  FILTER e.paperid != null AND e.institutionid != null
  INSERT MERGE({
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("Affiliations/", e.institutionid)
  }, e.authorid != null ? { authorid: e.authorid } : {}) INTO contributed_from
`);

db._query(`
FOR e IN grbench_update3_paperfields
  FILTER e.paperid != null AND e.fieldid != null
  INSERT {
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("Fields/", e.fieldid)
  } INTO PaperFields
`);
db._query(`
FOR t IN grbench_update3_link_nsf
  FILTER t.paperid != null AND t.award_id != null

  LET cleanPaper = TO_STRING(t.paperid)
  LET cleanAward = REGEX_REPLACE(TO_STRING(t.award_id), "[^a-zA-Z0-9_-]", "_")

  FILTER cleanPaper != "" AND cleanAward != ""

  INSERT {
    _from: CONCAT("Papers/", cleanPaper),
    _to: CONCAT("NSF_Metadata/", cleanAward)
  } INTO Link_NSF
  OPTIONS { ignoreErrors: true }
`)
db._query(`
FOR t IN grbench_update3_link_nih
  FILTER t.paperid != null AND t.award_id != null

  LET cleanPaper = TO_STRING(t.paperid)
  LET cleanAward = TO_STRING(t.award_id)

  INSERT {
    _from: CONCAT("Papers/", cleanPaper),
    _to: CONCAT("NIH_Metadata/", cleanAward)
  }
  INTO Link_NIH
  OPTIONS { ignoreErrors: true }
`)
db._query(`
FOR e IN grbench_update3_link_clinicaltrials
  FILTER e.paperid != null AND e.nct_id != null
  INSERT {
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("clinicaltrials_metadata/", e.nct_id)
  } INTO Link_ClinicalTrials
`);

db._query(`
FOR e IN grbench_update3_link_newsfeed
  FILTER e.paperid != null AND e.newsfeed_id != null
  INSERT {
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("Newsfeed_Metadata/", e.newsfeed_id)
  } INTO link_newsfeed
`);

db._query(`
FOR e IN grbench_update3_link_twitter
  FILTER e.paperid != null AND e.tweet_id != null
  INSERT {
    _from: CONCAT("Papers/", e.paperid),
    _to: CONCAT("Twitter_Metadata/", e.tweet_id)
  } INTO link_twitter
`);