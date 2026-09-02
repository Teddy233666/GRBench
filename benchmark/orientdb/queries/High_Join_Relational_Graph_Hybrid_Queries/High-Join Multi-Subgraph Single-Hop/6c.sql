SELECT
    $q0[0].v AS p3,
    $q1[0].v AS newsfeed,
    $q2[0].v AS minSource,
    $q3[0].v AS minNobel,
    $q4[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN ref.paperid AS paperid
)),
    $q1 = (SELECT MIN(newsfeed) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)}, {as:p}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n} RETURN n.newsfeed_id AS newsfeed
)),
    $q2 = (SELECT MIN(sourceid) AS v
FROM sources
WHERE sourceid IN (
    SELECT sourceid
    FROM papersources
    WHERE paperid IN (
        SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
    )
)),
    $q3 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
)),
    $q4 = (SELECT MIN(patent) AS v
FROM link_patents
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
));
