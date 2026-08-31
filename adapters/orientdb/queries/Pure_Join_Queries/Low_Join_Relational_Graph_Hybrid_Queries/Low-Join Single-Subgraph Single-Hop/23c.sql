SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count = 1 AND paperid IN (SELECT paperid FROM Link_NSF WHERE award_id IN (SELECT award_id FROM NSF_Metadata))),
    $q1 = (SELECT MIN(patent) AS v FROM link_patents WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid LIKE 'W423590139%' AND citation_count = 1 AND paperid IN (SELECT paperid FROM Link_NSF WHERE award_id IN (SELECT award_id FROM NSF_Metadata))));
