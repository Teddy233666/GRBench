SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minSource
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(sourceid) AS v
FROM sources
WHERE sourceid IN (
    SELECT sourceid
    FROM papersources
    WHERE paperid IN (
        SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
    )
));
