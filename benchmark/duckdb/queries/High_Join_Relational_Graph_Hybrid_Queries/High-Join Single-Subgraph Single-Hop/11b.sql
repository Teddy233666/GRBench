SELECT
    MIN(pn.paperid)            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(h0.paperid) AS minh0paperid
FROM
GRAPH_TABLE(
    sciscinet_graph
    MATCH (p IS Papers)-[pr IS  Link_NSF]->(n IS NSF_Metadata)
     WHERE p.paperid LIKE 'W423590139%'
      AND p.citation_count <=1
    COLUMNS (
        p.paperid AS paperid
    )
) pn

LEFT JOIN papersources ps_table
  ON pn.paperid = ps_table.paperid

LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid
LEFT JOIN link_nobellaureates ln
  ON pn.paperid = ln.paperid

LEFT JOIN hit_papers_level0 h0
  ON pn.paperid = h0.paperid;