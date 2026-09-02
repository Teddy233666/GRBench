SELECT
    MIN(pn.paperid)            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource,
    MIN(h1.paperid) AS minh1paperid,
    MIN(lp.patent) AS minPatent
FROM
GRAPH_TABLE(
    sciscinet_graph
      MATCH (p IS Papers)-[pr IS Link_ClinicalTrials]->(n IS clinicaltrials_metadata)
     WHERE p.paperid LIKE 'W423590139%'
      AND p.citation_count =1
    COLUMNS (
        p.paperid AS paperid
    )
) pn

LEFT JOIN papersources ps_table
  ON pn.paperid = ps_table.paperid

LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid
LEFT JOIN hit_papers_level1 h1
  ON pn.paperid = h1.paperid

LEFT JOIN link_patents lp
  ON pn.paperid = lp.paperid;