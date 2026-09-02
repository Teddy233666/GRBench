SELECT MIN(g.ref_paperid)
FROM GRAPH_TABLE(
    sciscinet_graph
    MATCH p = ANY SHORTEST
        (p IS Papers)-[r1 IS PaperReferences]->{,1}(ref IS Papers)
     WHERE p.paperid='W4211259235'
      AND ref.citation_count<150
     COLUMNS (
        p.paperid  AS paperid,
        ref.paperid AS ref_paperid,
        ref.citation_count AS citation_count
    )
)g;