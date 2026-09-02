SELECT
    $q0[0].v AS min_ref_paperid,
    $q1[0].v AS author,
    $q2[0].v AS newsfeed
LET
    $q0 = (SELECT MIN(p3) AS v
FROM (
    MATCH {class:Papers, as:p1, where:(paperid = 'W4235901390')}.out('PaperReferences'){class:Papers, as:p5}.out('PaperReferences'){class:Papers, as:p6}.out('PaperReferences'){class:Papers, as:p3} RETURN p3.paperid AS p3
)),
    $q1 = (SELECT MIN(author) AS v
FROM (
    MATCH {class:Papers, as:p1, where:(paperid = 'W4235901390')}.out('PaperReferences'){class:Papers, as:p5}.out('PaperReferences'){class:Papers, as:p6}.out('PaperReferences'){class:Papers, as:p3}, {as:p1}.in('Authors_Paper'){class:Authors_Gender, as:a} RETURN a.authorid AS author
)),
    $q2 = (SELECT MIN(newsfeed) AS v
FROM (
    MATCH {class:Papers, as:p1, where:(paperid = 'W4235901390')}.out('PaperReferences'){class:Papers, as:p5}.out('PaperReferences'){class:Papers, as:p6}.out('PaperReferences'){class:Papers, as:p3}, {as:p1}.out('link_newsfeed'){class:Newsfeed_Metadata, as:n} RETURN n.newsfeed_id AS newsfeed
));
