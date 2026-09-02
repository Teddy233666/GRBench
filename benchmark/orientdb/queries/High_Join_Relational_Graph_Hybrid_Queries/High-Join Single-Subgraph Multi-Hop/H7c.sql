SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minSource,
    $q2[0].v AS minNobel,
    $q3[0].v AS minPatent
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
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN ref.paperid AS paperid
)
    )
)),
    $q2 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
)),
    $q3 = (SELECT MIN(patent) AS v
FROM link_patents
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
));
