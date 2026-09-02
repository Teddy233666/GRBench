SELECT
    $q0[0].v AS p3,
    $q1[0].v AS newsfeed,
    $q2[0].v AS minNobel
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE citation_count < 80 AND paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208'))),
    $q1 = (SELECT MIN(newsfeed_id) AS v FROM Newsfeed_Metadata WHERE newsfeed_id IN (SELECT newsfeed_id FROM link_newsfeed WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 80))))),
    $q2 = (SELECT MIN(laureate_id) AS v FROM link_nobellaureates WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 80))));
