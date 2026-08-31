SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS fieldid,
    $q2[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 80))))))),
    $q1 = (SELECT MIN(fieldid) AS v FROM hit_papers_level0 WHERE paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208' AND paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT citing_paperid FROM PaperReferences WHERE cited_paperid IN (SELECT paperid FROM Papers WHERE citation_count < 80)))))))),
    $q2 = (SELECT MIN(patent) AS v FROM link_patents WHERE paperid IN (SELECT paperid FROM Papers WHERE citation_count < 80 AND paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208'))))))));
