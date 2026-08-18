
SELECT
    MIN(p123.p3::text),
    MIN(nf.newsfeed::text) AS newsfeed,
    MIN(s.sourceid::text) AS minSource,
    MIN(ln.laureate_id::text) AS minNobel,
    MIN(lp.patent::text) AS minPatent
FROM
cypher('sciscinet_graph', $$
    MATCH (p1:Papers)-[:PaperReferences]->(p5:Papers)
          -[:PaperReferences]->(p6:Papers)
          -[:PaperReferences]->(p3:Papers)
    WHERE p1.paperid = 'W4211259235'
    AND toInteger(p3.citation_count) < 5
    RETURN p1.paperid, p3.paperid
$$) AS p123(p1 agtype, p3 agtype)

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (p4:Papers)-[:link_newsfeed]->(n:Newsfeed_Metadata)
    RETURN p4.paperid, n.newsfeed_id
$$) AS nf(p4 agtype, newsfeed agtype)

ON p123.p1::text = nf.p4::text

LEFT JOIN papersources ps
  ON p123.p1::text = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON p123.p1::text = ln.paperid

LEFT JOIN link_patents lp
  ON p123.p1::text = lp.paperid;