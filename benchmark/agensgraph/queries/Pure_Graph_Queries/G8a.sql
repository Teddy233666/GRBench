SELECT
    MIN(REPLACE((p123.p3)::text, '"', '')),
    MIN(REPLACE((ap4.author)::text, '"', '')),
    MIN(REPLACE((nf.newsfeed)::text, '"', ''))
FROM
(
    MATCH (p1:Papers)-[r1:PaperReferences]->(p5:Papers)
          -[r2:PaperReferences]->(p6:Papers)
          -[r3:PaperReferences]->(p3:Papers)
    WHERE p1.paperid = 'W4235901390'
    RETURN
        p1.paperid AS p1,
        p3.paperid AS p3
) p123

LEFT JOIN
(
    MATCH (a:Authors_Gender)-[ap:Authors_Paper]->(p4:Papers)
    WHERE p4.is_retracted = FALSE
    RETURN
        a.authorid AS author,
        p4.paperid AS p4
) ap4
ON REPLACE((p123.p1)::text, '"', '') = REPLACE((ap4.p4)::text, '"', '')

LEFT JOIN
(
    MATCH (p4:Papers)-[nf:link_newsfeed]->(n:Newsfeed_Metadata)
    RETURN
        p4.paperid    AS p4,
        n.newsfeed_id AS newsfeed
) nf
ON REPLACE((p123.p1)::text, '"', '') = REPLACE((nf.p4)::text, '"', '');
