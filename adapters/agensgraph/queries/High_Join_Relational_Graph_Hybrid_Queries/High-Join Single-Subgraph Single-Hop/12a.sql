SELECT
    MIN(REPLACE((pn.paperid)::text, '"', ''))            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(h1.paperid) AS minh1paperid
FROM
(
    MATCH (p:Papers)-[pr:Link_ClinicalTrials]->(n:clinicaltrials_metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND p.citation_count <= 3
    RETURN
        p.paperid AS paperid
) pn


JOIN papersources ps_table
  ON REPLACE((pn.paperid)::text, '"', '') = ps_table.paperid


JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid


JOIN hit_papers_level1 h1
  ON REPLACE((pn.paperid)::text, '"', '') = h1.paperid


JOIN link_patents lp
  ON REPLACE((pn.paperid)::text, '"', '') = lp.paperid;