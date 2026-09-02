SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minNobel
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count <= 3 AND paperid IN (SELECT paperid FROM Link_ClinicalTrials WHERE nct_id IN (SELECT nct_id FROM clinicaltrials_metadata))),
    $q1 = (SELECT MIN(laureate_id) AS v FROM link_nobellaureates WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count <= 3 AND paperid IN (SELECT paperid FROM Link_ClinicalTrials WHERE nct_id IN (SELECT nct_id FROM clinicaltrials_metadata))));
