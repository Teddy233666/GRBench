db._create("Papers");
db._create("Authors_Gender");
db._create("Affiliations");
db._create("Fields");
db._create("NSF_Metadata");
db._create("NIH_Metadata");
db._create("clinicaltrials_metadata");
db._create("Newsfeed_Metadata");
db._create("Twitter_Metadata");
db._createEdgeCollection("Papers_to_Authors");
db._createEdgeCollection("Authors_Paper");
db._createEdgeCollection("affiliated_with");
db._createEdgeCollection("contributed_from");
db._createEdgeCollection("affl_assoc_affl");
db._createEdgeCollection("PaperReferences");
db._createEdgeCollection("Link_NSF");
db._createEdgeCollection("Link_NIH");
db._createEdgeCollection("Link_ClinicalTrials");
db._createEdgeCollection("link_newsfeed");
db._createEdgeCollection("link_twitter");
db._createEdgeCollection("PaperFields");
arangoimport --file {{UPDATE_DIR}}/grbench_update1_papers.csv --type csv --collection Papers --create-collection true --translate "paperid=_key" --server.password "" --threads 32 --server.request-timeout 3600 &&


arangoimport --file {{DATA_DIR}}/sciscinet_papers.csv --type csv --collection Papers --create-collection true --translate "paperid=_key" --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_authors.csv --type csv --collection Authors_Gender --create-collection true --translate "authorid=_key" --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_affiliations.csv --type csv --collection Affiliations --create-collection true --translate "institutionid=_key" --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_fields.csv --type csv --collection Fields --create-collection true --translate "fieldid=_key" --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_nsf_metadata.csv --type csv --collection NSF_Metadata --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_nih_metadata.csv --type csv --collection NIH_Metadata --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_clinicaltrials_metadata.csv --type csv --collection clinicaltrials_metadata --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_newsfeed_metadata.csv --type csv --collection Newsfeed_Metadata --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_twitter_metadata.csv --type csv --collection Twitter_Metadata --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_authors_paperid.csv --type csv --collection tmp_papers_authors --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_author_affiliation.csv --type csv --collection tmp_author_affiliation --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_paper_author_affiliation.csv --type csv --collection tmp_contributed --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_paperrefs.csv --type csv --collection tmp_paper_refs --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_nsf.csv --type csv --collection tmp_link_nsf --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_nih.csv --type csv --collection tmp_link_nih --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_clinicaltrials.csv --type csv --collection tmp_link_clinical --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_newsfeed.csv --type csv --collection tmp_link_newsfeed --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_twitter.csv --type csv --collection tmp_link_twitter --create-collection true --server.password "" --threads 32 --server.request-timeout 3600 &&
arangoimport --file {{DATA_DIR}}/sciscinet_paperfields.csv --type csv --collection tmp_paper_fields --create-collection true --server.password "" --threads 32 --server.request-timeout 3600
arangoimport  --file {{DATA_DIR}}/sciscinet_affl_assoc_affl.csv --type csv --collection tmp_affl_assoc --create-collection true --server.password "" --threads 32 --server.request-timeout 3600

arangoimport \
  --file {{DATA_DIR}}/sciscinet_affl_assoc_affl.csv \
  --type csv \
  --collection tmp_affl_assoc \
  --create-collection true
 db._query(`
FOR t IN tmp_papers_authors
FILTER t.paperid != null AND t.authorid != null
INSERT {
  _from: CONCAT("Authors_Gender/", t.authorid),
  _to: CONCAT("Papers/", t.paperid)
}
INTO Authors_Paper
`)
db._query(`
FOR t IN tmp_paper_refs
  FILTER t.citing_paperid != null AND t.cited_paperid != null
  INSERT {
    _from: CONCAT("Papers/", t.citing_paperid),
    _to: CONCAT("Papers/", t.cited_paperid)
  } INTO PaperReferences
`)
db._query(`
FOR t IN tmp_author_affiliation
FILTER t.authorid != null AND t.institutionid != null
INSERT {
  _from: CONCAT("Authors_Gender/", t.authorid),
  _to: CONCAT("Affiliations/", t.institutionid)
}
INTO affiliated_with
`)
db._query(`
FOR t IN tmp_contributed
FILTER t.paperid != null AND t.institutionid != null
INSERT {
  _from: CONCAT("Papers/", t.paperid),
  _to: CONCAT("Affiliations/", t.institutionid),
  authorid: t.authorid
}
INTO contributed_from
`)
db._query(`
FOR t IN tmp_affl_assoc
FILTER t.institutionid != null AND t.associated_institution_id != null
INSERT {
  _from: CONCAT("Affiliations/", t.institutionid),
  _to: CONCAT("Affiliations/", t.associated_institution_id),
  relationship: t.relationship
}
INTO affl_assoc_affl
OPTIONS { waitForSync: false, limit: 20000 }
`)
db._query(`
FOR t IN tmp_link_nsf
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
FOR t IN tmp_link_nih
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
FOR t IN tmp_link_clinical
FILTER t.paperid != null AND t.nct_id != null
INSERT {
  _from: CONCAT("Papers/", t.paperid),
  _to: CONCAT("clinicaltrials_metadata/", t.nct_id)
}
INTO Link_ClinicalTrials
`)
db._query(`
FOR t IN tmp_link_newsfeed
FILTER t.paperid != null AND t.newsfeed_id != null
INSERT {
  _from: CONCAT("Papers/", t.paperid),
  _to: CONCAT("Newsfeed_Metadata/", t.newsfeed_id)
}
INTO link_newsfeed
`)
db._query(`
FOR t IN tmp_link_twitter
  FILTER t.paperid != null AND t.tweet_id != null

  LET cleanPaper = TO_STRING(t.paperid)
  LET cleanTweet = REGEX_REPLACE(
    TO_STRING(t.tweet_id),
    "[^a-zA-Z0-9_-]",
    "_"
  )

  FILTER cleanPaper != "" AND cleanTweet != ""

  INSERT {
    _from: CONCAT("Papers/", cleanPaper),
    _to: CONCAT("Twitter_Metadata/", cleanTweet)
  }
  INTO link_twitter
  OPTIONS { ignoreErrors: true }
`)
db._query(`
FOR t IN tmp_paper_fields
FILTER t.paperid != null AND t.fieldid != null
INSERT {
  _from: CONCAT("Papers/", t.paperid),
  _to: CONCAT("Fields/", t.fieldid)
}
INTO PaperFields
`)
arangoimport --file {{DATA_DIR}}/sciscinet_author_details.csv --type csv --collection author_details --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/hit_papers_level0.csv --type csv --collection hit_papers_level0 --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/hit_papers_level1.csv --type csv --collection hit_papers_level1 --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/normalized_citations_level0.csv --type csv --collection normalized_citations_level0 --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/normalized_citations_level1.csv --type csv --collection normalized_citations_level1 --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/sciscinet_sources.csv --type csv --collection sources --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/sciscinet_papersources.csv --type csv --collection papersources --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_nobellaureates.csv --type csv --collection link_nobellaureates --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/sciscinet_link_patents.csv --type csv --collection link_patents --create-collection true --server.password "" --threads 32 --server.request-timeout 3200 &&
arangoimport --file {{DATA_DIR}}/sciscinet_paperdetails.csv --type csv --collection PaperDetails --create-collection true --server.password "" --threads 32 --server.request-timeout 3200

arangoimport \
  --file {{UPDATE_DIR}}/grbench_update22_edges.csv \
  --type csv \
  --collection grbench_update2_edges \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_paperreferences.csv \
  --type csv \
  --collection grbench_update3_paperreferences \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600


    arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_papers_to_authors.csv \
  --type csv \
  --collection grbench_update3_papers_to_authors \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_contributed_from.csv \
  --type csv \
  --collection grbench_update3_contributed_from \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_paperfields.csv \
  --type csv \
  --collection grbench_update3_paperfields \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_link_nsf.csv \
  --type csv \
  --collection grbench_update3_link_nsf \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_link_nih.csv \
  --type csv \
  --collection grbench_update3_link_nih \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_link_clinicaltrials.csv \
  --type csv \
  --collection grbench_update3_link_clinicaltrials \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_link_newsfeed.csv \
  --type csv \
  --collection grbench_update3_link_newsfeed \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600

  arangoimport \
  --file {{UPDATE_DIR}}/grbench_update3_link_twitter.csv \
  --type csv \
  --collection grbench_update3_link_twitter \
  --create-collection true \
  --server.password "" \
  --threads 32 \
  --server.request-timeout 3600
