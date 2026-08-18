// 删除 Papers 2013–2015 及相关边；需先运行 backup.js
var BATCH = { batchSize: 5000 };

db._query(`
FOR e IN grbench_update3_paperreferences
  FILTER e.citing_paperid != null AND e.cited_paperid != null
  COLLECT citing = e.citing_paperid, cited = e.cited_paperid
  LET fromId = CONCAT("Papers/", citing)
  LET toId   = CONCAT("Papers/", cited)
  FOR r IN PaperReferences
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN PaperReferences
`, {}, BATCH);

db._query(`
FOR e IN grbench_update3_papers_to_authors
  FILTER e.authorid != null AND e.paperid != null
  COLLECT authorid = e.authorid, paperid = e.paperid
  LET fromId = CONCAT("Authors_Gender/", authorid)
  LET toId   = CONCAT("Papers/", paperid)
  FOR r IN Authors_Paper
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN Authors_Paper
`, {}, 5000);

db._query(`
FOR e IN grbench_update3_contributed_from
  FILTER e.paperid != null AND e.institutionid != null
  COLLECT paperid = e.paperid, institutionid = e.institutionid, authorid = e.authorid
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("Affiliations/", institutionid)
  FOR r IN contributed_from
    FILTER r._from == fromId AND r._to == toId
    FILTER authorid == null OR r.authorid == authorid
    REMOVE r IN contributed_from
`, {}, 5000);

db._query(`
FOR e IN grbench_update3_paperfields
  FILTER e.paperid != null AND e.fieldid != null
  COLLECT paperid = e.paperid, fieldid = e.fieldid
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("Fields/", fieldid)
  FOR r IN PaperFields
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN PaperFields
`, {}, 5000);

db._query(`
FOR e IN grbench_update3_link_nsf
  FILTER e.paperid != null AND e.award_id != null
  COLLECT paperid = e.paperid, award_id = e.award_id
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("NSF_Metadata/", award_id)
  FOR r IN Link_NSF
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN Link_NSF
`, {}, 5000);

db._query(`
FOR e IN grbench_update3_link_nih
  FILTER e.paperid != null AND e.award_id != null
  COLLECT paperid = e.paperid, award_id = e.award_id
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("NIH_Metadata/", award_id)
  FOR r IN Link_NIH
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN Link_NIH
`, {}, BATCH);

db._query(`
FOR e IN grbench_update3_link_clinicaltrials
  FILTER e.paperid != null AND e.nct_id != null
  COLLECT paperid = e.paperid, nct_id = e.nct_id
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("clinicaltrials_metadata/", nct_id)
  FOR r IN Link_ClinicalTrials
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN Link_ClinicalTrials
`, {}, BATCH);

db._query(`
FOR e IN grbench_update3_link_newsfeed
  FILTER e.paperid != null AND e.newsfeed_id != null
  COLLECT paperid = e.paperid, newsfeed_id = e.newsfeed_id
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("Newsfeed_Metadata/", newsfeed_id)
  FOR r IN link_newsfeed
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN link_newsfeed
`, {}, BATCH);

db._query(`
FOR e IN grbench_update3_link_twitter
  FILTER e.paperid != null AND e.tweet_id != null
  COLLECT paperid = e.paperid, tweet_id = e.tweet_id
  LET fromId = CONCAT("Papers/", paperid)
  LET toId   = CONCAT("Twitter_Metadata/", tweet_id)
  FOR r IN link_twitter
    FILTER r._from == fromId AND r._to == toId
    REMOVE r IN link_twitter
`, {}, BATCH);
