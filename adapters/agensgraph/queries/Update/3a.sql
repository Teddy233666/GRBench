LOAD FROM grbench_update3_papers AS p
CREATE (:Papers = to_jsonb(row_to_json(p)));

LOAD FROM grbench_update3_paperreferences AS e
MATCH (p1:Papers), (p2:Papers)
WHERE p1.paperid = e.citing_paperid
  AND p2.paperid = e.cited_paperid
CREATE (p1)-[:PaperReferences]->(p2);

LOAD FROM grbench_update3_papers_to_authors AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (a:Authors_Gender {authorid: e.authorid})
MERGE (p)-[:Papers_to_Authors]->(a);

LOAD FROM grbench_update3_contributed_from AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (i:Affiliations {institutionid: e.institutionid})
MERGE (p)-[:contributed_from {authorid: e.authorid}]->(i);

LOAD FROM grbench_update3_paperfields AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (f:Fields {fieldid: e.fieldid})
MERGE (p)-[:PaperFields]->(f);

LOAD FROM grbench_update3_link_nsf AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (m:NSF_Metadata {award_id: e.award_id})
MERGE (p)-[:Link_NSF]->(m);

LOAD FROM grbench_update3_link_nih AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (m:NIH_Metadata {award_id: e.award_id})
MERGE (p)-[:Link_NIH]->(m);

LOAD FROM grbench_update3_link_clinicaltrials AS e
MATCH (p:Papers), (c:clinicaltrials_metadata)
WHERE p.paperid = e.paperid
  AND c.nct_id = e.nct_id
CREATE (p)-[:Link_ClinicalTrials]->(c);

LOAD FROM grbench_update3_link_newsfeed AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (n:Newsfeed_Metadata {newsfeed_id: e.newsfeed_id})
MERGE (p)-[:link_newsfeed]->(n);

LOAD FROM grbench_update3_link_twitter AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (t:Twitter_Metadata {tweet_id: e.tweet_id})
MERGE (p)-[:link_twitter]->(t);