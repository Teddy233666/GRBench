SELECT
    $q0[0].v AS p3,
    $q1[0].v AS fieldid
LET
    $q0 = (SELECT MIN(p3) AS v
FROM (
    MATCH {class:Papers, as:p1, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p5}.out('PaperReferences'){class:Papers, as:p6}.out('PaperReferences'){class:Papers, as:p3, where:(citation_count < 150)} RETURN p3.paperid AS p3
)),
    $q1 = (SELECT MIN(fieldid) AS v
FROM (
    MATCH {class:Papers, as:p1, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p5}.out('PaperReferences'){class:Papers, as:p6}.out('PaperReferences'){class:Papers, as:p3, where:(citation_count < 150)}, {as:p3}.out('PaperFields'){class:Fields, as:f} RETURN f.fieldid AS fieldid
));
