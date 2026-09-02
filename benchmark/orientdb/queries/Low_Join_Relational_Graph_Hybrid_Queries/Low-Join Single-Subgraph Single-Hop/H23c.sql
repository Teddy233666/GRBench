SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NSF'){class:NSF_Metadata, as:n} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(patent) AS v
FROM link_patents
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NSF'){class:NSF_Metadata, as:n} RETURN p.paperid AS paperid
)
));
