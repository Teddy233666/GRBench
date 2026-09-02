SELECT
    $q0[0].v AS minPaper,
    $q1[0].v AS minAuthor1,
    $q2[0].v AS award_id,
    $q3[0].v AS minNobel,
    $q4[0].v AS minAuthorid2
LET
    $q0 = (SELECT MIN(paperid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)} RETURN p.paperid AS paperid
)),
    $q1 = (SELECT MIN(authorid) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)}, {as:ref}.in('Authors_Paper'){class:Authors_Gender, as:a, where:(h_index > 10)} RETURN a.authorid AS authorid
)),
    $q2 = (SELECT MIN(award_id) AS v
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)}, {as:p}.out('Link_NSF'){class:NSF_Metadata, as:nsf} RETURN nsf.award_id AS award_id
)),
    $q3 = (SELECT MIN(laureate_id) AS v
FROM link_nobellaureates
WHERE paperid IN (
    SELECT paperid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)} RETURN p.paperid AS paperid
)
)),
    $q4 = (SELECT MIN(authorid) AS v
FROM author_details
WHERE authorid IN (
    SELECT authorid
FROM (
    MATCH {class:Papers, as:p, where:(paperid = 'W2122344208')}.out('PaperReferences'){class:Papers, as:p1}.out('PaperReferences'){class:Papers, as:p2}.out('PaperReferences'){class:Papers, as:ref, where:(citation_count < 150)}, {as:ref}.in('Authors_Paper'){class:Authors_Gender, as:a, where:(h_index > 10)} RETURN a.authorid AS authorid
)
));
