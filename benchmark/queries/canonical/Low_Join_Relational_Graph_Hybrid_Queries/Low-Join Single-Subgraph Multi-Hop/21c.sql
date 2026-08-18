SELECT
    MIN(pr.paperid)            AS cited_paperid,
    MIN(h0.fieldid) AS fieldid,
    MIN(lp.patent) AS minPatent
FROM

GRAPH_TABLE(
    sciscinet_graph
    MATCH (orig IS Papers)-[r1 IS PaperReferences]->(p2 IS Papers)-[r2 IS PaperReferences]->(p3 IS Papers)-[r3 IS PaperReferences]->(cited IS Papers)
     WHERE orig.paperid='W2122344208'
     AND cited.citation_count<5
    COLUMNS (
        orig.paperid AS paperid,
        cited.paperid AS cited_paperid
    )
) pr
LEFT JOIN hit_papers_level0 h0
  ON pr.paperid = h0.paperid
LEFT JOIN link_patents lp
  ON pr.cited_paperid = lp.paperid;