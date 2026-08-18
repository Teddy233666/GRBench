SELECT
    MIN(pn.paperid::text)            AS cited_paperid,
    MIN(src_table.sourceid::text) AS minSource,
    MIN(ln.laureate_id::text) AS minNobel,
    MIN(lp.patent::text) AS minPatent
FROM

cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_NIH]->(n:NIH_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
    AND toInteger(p.citation_count)<= 3
    RETURN p.paperid
$$) AS pn(paperid agtype)

LEFT JOIN papersources ps_table
  ON pn.paperid::text = ps_table.paperid

LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid

LEFT JOIN link_nobellaureates ln
  ON pn.paperid::text = ln.paperid

LEFT JOIN link_patents lp
  ON pn.paperid::text = lp.paperid;