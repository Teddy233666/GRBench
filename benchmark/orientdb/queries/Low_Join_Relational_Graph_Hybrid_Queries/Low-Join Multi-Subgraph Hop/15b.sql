SELECT
    $q0[0].v AS p3,
    $q1[0].v AS fieldid,
    $q2[0].v AS newsfeed,
    $q3[0].v AS minNobel
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)} RETURN ref.paperid AS paperid
)),
    $q1 = (SELECT MIN(fieldid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)}, {as:ref}.out('PaperFields'){class:Fields, as:f} RETURN f.fieldid AS fieldid
)),
    $q2 = (SELECT MIN(newsfeed) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)}, {as:p}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n} RETURN n.newsfeed_id AS newsfeed
)),
    $q3 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 80)} RETURN p.paperid AS paperid
)
));
