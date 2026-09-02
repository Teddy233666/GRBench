SELECT
    MIN(p123.p3),
    MIN(nf.newsfeed) AS newsfeed,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
GRAPH_TABLE(
    sciscinet_graph
   MATCH (p1 IS Papers)-[r3 IS PaperReferences]->(p3 IS Papers)
   WHERE p1.paperid='W4211259235'
      AND p3.citation_count<150
    COLUMNS(
        p1.paperid AS p1,
        p3.paperid AS p3
    )
) p123
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (p4 IS Papers)
            -[nf IS link_newsfeed]->
        (n IS Newsfeed_Metadata)
    COLUMNS(
        p4.paperid    AS p4,
        n.newsfeed_id AS newsfeed
    )
) nf
ON p123.p1  = nf.p4
LEFT JOIN papersources ps
  ON p123.p1  = ps.paperid
LEFT JOIN sources s
  ON ps.sourceid = s.sourceid
LEFT JOIN link_nobellaureates ln
  ON p123.p1  = ln.paperid
LEFT JOIN link_patents lp
  ON p123.p1 = lp.paperid;