SELECT
    $q0[0].v AS minPaper,
    $q1[0].v AS award_id,
    $q2[0].v AS minNobel,
    $q3[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 5))),
    $q1 = (SELECT MIN(award_id) AS v FROM NSF_Metadata WHERE award_id IN (SELECT award_id FROM Link_NSF WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 5))))),
    $q2 = (SELECT MIN(laureate_id) AS v FROM link_nobellaureates WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 5)))),
    $q3 = (SELECT MIN(patent) AS v FROM link_patents WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 5))));
