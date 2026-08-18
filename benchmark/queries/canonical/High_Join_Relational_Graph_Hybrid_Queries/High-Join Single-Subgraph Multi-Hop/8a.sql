SELECT
    MIN(pr.paperid)            AS cited_paperid,
    MIN(h0.fieldid) AS fieldid,
    MIN(h1.fieldid) AS fieldid,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM

GRAPH_TABLE(
    sciscinet_graph
    MATCH (orig IS Papers)-[r1 IS PaperReferences]->(p2 IS Papers)-[r2 IS PaperReferences]->(p3 IS Papers)-[r3 IS PaperReferences]->(cited IS Papers)
    WHERE orig.paperid='W2122344208'
    AND cited.citation_count<150
    COLUMNS (
        orig.paperid AS paperid,
        cited.paperid AS cited_paperid,
        cited.citation_count AS citation_count
    )
) pr

LEFT JOIN hit_papers_level0 h0
  ON pr.paperid = h0.paperid

LEFT JOIN hit_papers_level1 h1
  ON pr.paperid = h1.paperid

LEFT JOIN link_nobellaureates ln
  ON pr.cited_paperid = ln.paperid

LEFT JOIN link_patents lp
  ON pr.cited_paperid = lp.paperid;
