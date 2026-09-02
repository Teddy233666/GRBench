SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minSource
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150))))))),
    $q1 = (SELECT MIN(sourceid) AS v FROM sources WHERE sourceid IN (SELECT sourceid FROM papersources WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 150)))))))));
