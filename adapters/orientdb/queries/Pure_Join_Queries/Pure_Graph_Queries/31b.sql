SELECT
    $q0[0].v AS p3,
    $q1[0].v AS fieldid
LET
    $q0 = (SELECT MIN(paperid) AS v FROM Papers WHERE citation_count < 80 AND paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208'))))))),
    $q1 = (SELECT MIN(fieldid) AS v FROM Fields WHERE fieldid IN (SELECT fieldid FROM PaperFields WHERE paperid IN (SELECT paperid FROM Papers WHERE citation_count < 80 AND paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid IN (SELECT paperid FROM Papers WHERE paperid = 'W2122344208')))))))));
