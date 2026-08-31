SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minSource,
    $q2[0].v AS minNobel,
    $q3[0].v AS minh0paperid
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count = 1 AND paperid IN (SELECT paperid FROM Link_NSF WHERE award_id IN (SELECT award_id FROM NSF_Metadata))),
    $q1 = (SELECT MIN(sourceid) AS v FROM sources WHERE sourceid IN (SELECT sourceid FROM papersources WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count = 1 AND paperid IN (SELECT paperid FROM Link_NSF WHERE award_id IN (SELECT award_id FROM NSF_Metadata))))),
    $q2 = (SELECT MIN(laureate_id) AS v FROM link_nobellaureates WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count = 1 AND paperid IN (SELECT paperid FROM Link_NSF WHERE award_id IN (SELECT award_id FROM NSF_Metadata)))),
    $q3 = (SELECT MIN(paperid) AS v FROM hit_papers_level0 WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count = 1 AND paperid IN (SELECT paperid FROM Link_NSF WHERE award_id IN (SELECT award_id FROM NSF_Metadata))));
