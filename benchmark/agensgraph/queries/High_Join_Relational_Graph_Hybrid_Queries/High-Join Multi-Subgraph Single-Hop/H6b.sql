SELECT
    MIN(REPLACE((p123.p3)::text, '"', '')),
    MIN(REPLACE((nf.newsfeed)::text, '"', '')) AS newsfeed,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
    MATCH (p1:Papers)-[r1:PaperReferences]->(p3:Papers)
    WHERE p1.paperid='W4211259235'
    AND p3.citation_count<80
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


LEFT JOIN papersources ps
  ON REPLACE((p123.p1)::text, '"', '') = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON REPLACE((p123.p1)::text, '"', '') = ln.paperid

LEFT JOIN link_patents lp
  ON REPLACE((p123.p1)::text, '"', '') = lp.paperid;