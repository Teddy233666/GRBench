SELECT
    $q0[0].v AS minPaper,
    $q1[0].v AS minAuthor,
    $q2[0].v AS minSource,
    $q3[0].v AS minNobel,
    $q4[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid = 'W4211259235' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150))),
    $q1 = (SELECT MIN(authorid) AS v FROM Authors_Gender WHERE h_index > 10 AND authorid IN (SELECT authorid FROM Authors_Paper WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W4211259235' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150))))),
    $q2 = (SELECT MIN(sourceid) AS v FROM sources WHERE sourceid IN (SELECT sourceid FROM papersources WHERE paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150 AND paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W4211259235'))))),
    $q3 = (SELECT MIN(laureate_id) AS v FROM link_nobellaureates WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W4211259235' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150)))),
    $q4 = (SELECT MIN(authorid) AS v FROM author_details WHERE authorid IN (SELECT authorid FROM Authors_Gender WHERE h_index > 10 AND authorid IN (SELECT authorid FROM Authors_Paper WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W4211259235' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150))))));
