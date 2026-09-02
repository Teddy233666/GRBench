SELECT
    MIN(pr.paperid)            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM

GRAPH_TABLE(
    sciscinet_graph
    MATCH (orig IS Papers)-[r1 IS PaperReferences]->(p2 IS Papers)-[r2 IS PaperReferences]->(p3 IS Papers)-[r3 IS PaperReferences]->(cited IS Papers)
    WHERE orig.paperid='W2122344208'
    AND cited.citation_count<80
    COLUMNS (
         orig.paperid AS paperid,
        cited.paperid AS cited_paperid,
        cited.citation_count AS citation_count
    )
) pr

LEFT JOIN papersources ps_table
  ON pr.cited_paperid = ps_table.paperid

LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid

LEFT JOIN link_nobellaureates ln
  ON pr.paperid = ln.paperid

LEFT JOIN link_patents lp
  ON pr.paperid = lp.paperid;