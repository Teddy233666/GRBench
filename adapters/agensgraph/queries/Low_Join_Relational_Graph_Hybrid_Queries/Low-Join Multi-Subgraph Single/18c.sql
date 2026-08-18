SELECT
    MIN(REPLACE((p123.p3)::text, '"', '')),
    MIN(REPLACE((nf.newsfeed)::text, '"', '')) AS newsfeed,
    MIN(ln.laureate_id) AS minNobel
FROM
(
    MATCH (p1:Papers)-[r1:PaperReferences]->(p3:Papers)
    WHERE p1.paperid = 'W2122344208'
    AND p3.citation_count<5
    RETURN
        p1.paperid AS p1,
        p3.paperid AS p3
) p123


LEFT JOIN
(
    MATCH (p4:Papers)-[nf:link_newsfeed]->(n:Newsfeed_Metadata)
    RETURN
        p4.paperid    AS p4,
        n.newsfeed_id AS newsfeed
) nf
ON REPLACE((p123.p1)::text, '"', '') = REPLACE((nf.p4)::text, '"', '')


LEFT JOIN link_nobellaureates ln
  ON REPLACE((p123.p1)::text, '"', '') = ln.paperid;