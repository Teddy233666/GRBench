SELECT
    MIN(pr.paperid)            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource
FROM

GRAPH_TABLE(
    sciscinet_graph
    MATCH (orig IS Papers)-[r1 IS PaperReferences]->(p2 IS Papers)-[r2 IS PaperReferences]->(p3 IS Papers)-[r3 IS PaperReferences]->(cited IS Papers)
    WHERE orig.paperid='W2122344208'
    AND cited.citation_count<150
    COLUMNS (
         orig.paperid AS paperid,
        cited.paperid AS cited_paperid
    )
) pr
LEFT JOIN papersources ps_table
  ON pr.paperid = ps_table.paperid

LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid;
