SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS minNobel
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NIH'){class:NIH_Metadata, as:n} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NIH'){class:NIH_Metadata, as:n} RETURN p.paperid AS paperid
)
));
