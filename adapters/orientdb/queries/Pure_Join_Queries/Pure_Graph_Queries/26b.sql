SELECT
    $q0[0].v AS cited_paperid
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count <= 1 AND paperid IN (SELECT paperid FROM Link_NIH WHERE award_id IN (SELECT award_id FROM NIH_Metadata)));
