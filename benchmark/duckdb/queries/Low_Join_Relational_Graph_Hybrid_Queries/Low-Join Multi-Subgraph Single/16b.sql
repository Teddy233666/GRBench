SELECT
    MIN(g_ref.paperid) AS minPaper,
    MIN(g_ap.authorid) AS minAuthor,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
GRAPH_TABLE(
    sciscinet_graph
    MATCH (p IS Papers)-[r1 IS PaperReferences]->(ref IS Papers)
    WHERE p.paperid='W4211259235'
      AND ref.citation_count<80
    COLUMNS (
        p.paperid  AS paperid,
        ref.paperid AS ref_paperid,
        ref.citation_count AS citation_count
    )
) g_ref
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH (a IS Authors_Gender)-[ap IS Authors_Paper]->(p IS Papers)
    WHERE a.h_index>30
    COLUMNS (
        a.authorid     AS authorid,
        p.paperid      AS paperid
    )
) g_ap
ON g_ap.paperid = g_ref.paperid
LEFT JOIN link_nobellaureates ln
  ON g_ref.paperid  = ln.paperid
LEFT JOIN author_details ad
  ON g_ap.authorid = ad.authorid;
