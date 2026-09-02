SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minSource,
    $q2[0].v AS minh1paperid,
    $q3[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_ClinicalTrials'){class:clinicaltrials_metadata, as:n} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(sourceid) AS v
FROM sources
WHERE sourceid IN (
    SELECT sourceid
    FROM papersources
    WHERE paperid IN (
        SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_ClinicalTrials'){class:clinicaltrials_metadata, as:n} RETURN p.paperid AS paperid
)
    )
)),
    $q2 = (SELECT MIN(paperid) AS v
FROM hit_papers_level1
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_ClinicalTrials'){class:clinicaltrials_metadata, as:n} RETURN p.paperid AS paperid
)
)),
    $q3 = (SELECT MIN(patent) AS v
FROM link_patents
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_ClinicalTrials'){class:clinicaltrials_metadata, as:n} RETURN p.paperid AS paperid
)
));
