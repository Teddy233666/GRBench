SELECT
    $q0[0].v AS cited_paperid
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NIH'){class:NIH_Metadata, as:n} RETURN p.paperid AS paperid
));
