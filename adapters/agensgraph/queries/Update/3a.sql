LOAD FROM grbench_update3_paperreferences AS e
MATCH (p1:Papers)-[r:PaperReferences]->(p2:Papers)
WHERE p1.paperid = e.citing_paperid
  AND p2.paperid = e.cited_paperid
DELETE r;

LOAD FROM grbench_update3_papers_to_authors AS backup
MATCH (p:Papers)-[e:Papers_to_Authors]->(a:Authors_Gender)
WHERE p.paperid = backup.paperid
  AND a.authorid = backup.authorid
DELETE e;

LOAD FROM grbench_update3_Authors_Paper AS backup
MATCH (a:Authors_Gender)-[ap_rel:Authors_Paper]->(p:Papers)
WHERE p.paperid = backup.paperid
  AND a.authorid = backup.authorid
DELETE ap_rel;

LOAD FROM grbench_update3_contributed_from AS backup
MATCH (p:Papers)-[cf:contributed_from]->(i:Affiliations)
WHERE p.paperid = backup.paperid
  AND i.institutionid = backup.institutionid
  AND cf.authorid = backup.authorid
DELETE cf;

LOAD FROM grbench_update3_paperfields AS backup
MATCH (p:Papers)-[pf:PaperFields]->(f:Fields)
WHERE p.paperid = backup.paperid
  AND f.fieldid = backup.fieldid
DELETE pf;

LOAD FROM grbench_update3_link_nsf AS backup
MATCH (p:Papers)-[ln:Link_NSF]->(m:NSF_Metadata)
WHERE p.paperid = backup.paperid
  AND m.award_id = backup.award_id
DELETE ln;


LOAD FROM grbench_update3_link_nih AS backup
MATCH (p:Papers)-[ln:Link_NIH]->(m:NIH_Metadata)
WHERE p.paperid = backup.paperid
  AND m.award_id = backup.award_id
DELETE ln;

LOAD FROM grbench_update3_link_clinicaltrials AS backup
MATCH (p:Papers)-[lc:Link_ClinicalTrials]->(c:clinicaltrials_metadata)
WHERE p.paperid = backup.paperid
  AND c.nct_id = backup.nct_id
DELETE lc;

LOAD FROM grbench_update3_link_newsfeed AS backup
MATCH (p:Papers)-[nf:link_newsfeed]->(n:Newsfeed_Metadata)
WHERE p.paperid = backup.paperid
  AND n.newsfeed_id = backup.newsfeed_id
DELETE nf;

LOAD FROM grbench_update3_link_twitter AS backup
MATCH (p:Papers)-[tw:link_twitter]->(t:Twitter_Metadata)
WHERE p.paperid = backup.paperid
  AND t.tweet_id = backup.tweet_id
DELETE tw;

MATCH (p:Papers)
WHERE p.year >= 2020 AND p.year <= 2025
DELETE p;