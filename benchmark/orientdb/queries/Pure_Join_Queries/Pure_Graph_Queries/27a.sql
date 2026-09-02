SELECT
    $q0[0].v AS paperid,
    $q1[0].v AS award_id
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count <= 3 AND paperid IN (SELECT paperid FROM Link_NIH WHERE award_id IN (SELECT award_id FROM NIH_Metadata))),
    $q1 = (SELECT MIN(award_id) AS v FROM NSF_Metadata WHERE award_id IN (SELECT award_id FROM Link_NSF WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count <= 3 AND paperid IN (SELECT paperid FROM Link_NIH WHERE award_id IN (SELECT award_id FROM NIH_Metadata)))));
