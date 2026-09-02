SELECT
    $q0[0].v AS cited_paperid,
    $q1[0].v AS fieldid,
    $q2[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(fieldid) AS v
FROM hit_papers_level0
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)} RETURN p.paperid AS paperid
)
)),
    $q2 = (SELECT MIN(patent) AS v
FROM link_patents
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)} RETURN ref.paperid AS paperid
)
));
