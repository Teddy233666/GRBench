SELECT
    $q0[0].v AS minPaper,
    $q1[0].v AS award_id,
    $q2[0].v AS minNobel,
    $q3[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(award_id) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)}, {as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf} RETURN nsf.award_id AS award_id
)),
    $q2 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)} RETURN p.paperid AS paperid
)
)),
    $q3 = (SELECT MIN(patent) AS v
FROM link_patents
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)} RETURN ref.paperid AS paperid
)
));
