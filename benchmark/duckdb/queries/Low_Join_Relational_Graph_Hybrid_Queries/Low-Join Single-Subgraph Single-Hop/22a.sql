SELECT
    MIN(pn.paperid)            AS cited_paperid,
    MIN(ln.laureate_id) AS minNobel
FROM
GRAPH_TABLE(
    sciscinet_graph
    MATCH (p IS Papers)-[pr IS  Link_NIH]->(n IS NIH_Metadata)
     WHERE p.paperid LIKE 'W423590139%'
      AND p.citation_count <=3
    COLUMNS (
        p.paperid AS paperid
    )
) pn
LEFT JOIN link_nobellaureates ln
  ON pn.paperid = ln.paperid;
