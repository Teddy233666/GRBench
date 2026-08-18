SELECT
    $q0[0].v AS paperid,
    $q1[0].v AS award_id
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NIH'){class:NIH_Metadata, as:nih} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(award_id) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid LIKE 'W423590139%' AND citation_count = 1)}.out('Link_NIH'){class:NIH_Metadata, as:nih}, {as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf} RETURN nsf.award_id AS award_id
));
