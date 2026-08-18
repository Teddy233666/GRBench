SELECT
    MIN(REPLACE((pn.paperid)::text, '"', ''))            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
    MATCH (p:Papers)-[pr:Link_NIH]->(n:NIH_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND p.citation_count <= 1
    RETURN
        p.paperid AS paperid
) pn


JOIN papersources ps_table
  ON REPLACE((pn.paperid)::text, '"', '') = ps_table.paperid


JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid


JOIN link_nobellaureates ln
  ON REPLACE((pn.paperid)::text, '"', '') = ln.paperid


JOIN link_patents lp
  ON REPLACE((pn.paperid)::text, '"', '') = lp.paperid;