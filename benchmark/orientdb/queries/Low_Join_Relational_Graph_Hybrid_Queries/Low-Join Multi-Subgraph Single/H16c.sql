SELECT
    $q0[0].v AS minPaper,
    $q1[0].v AS minAuthor,
    $q2[0].v AS minNobel,
    $q3[0].v AS minPatent
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(authorid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)}, {as:p}.in('Authors_Paper'){class:Authors_Gender, as:a, where:(h_index > 80)} RETURN a.authorid AS authorid
)),
    $q2 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)} RETURN p.paperid AS paperid
)
)),
    $q3 = (SELECT MIN(authorid) AS v
FROM author_details
WHERE authorid IN (
    SELECT authorid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W4211259235')}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 5)}, {as:p}.in('Authors_Paper'){class:Authors_Gender, as:a, where:(h_index > 80)} RETURN a.authorid AS authorid
)
));
