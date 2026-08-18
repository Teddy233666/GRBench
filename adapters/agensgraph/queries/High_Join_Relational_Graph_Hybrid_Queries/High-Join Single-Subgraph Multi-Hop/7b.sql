SELECT
    MIN(REPLACE((pr.paperid)::text, '"', ''))            AS cited_paperid,
    MIN(src_table.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
    MATCH (orig:Papers)-[r1:PaperReferences]->(p2:Papers)
          -[r2:PaperReferences]->(p3:Papers)
          -[r3:PaperReferences]->(cited:Papers)
     WHERE orig.paperid='W2122344208'
     AND cited.citation_count<80
    RETURN
        orig.paperid AS paperid,
        cited.paperid AS cited_paperid
) pr


LEFT JOIN papersources ps_table
  ON REPLACE((pr.cited_paperid)::text, '"', '') = ps_table.paperid


LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid


LEFT JOIN link_nobellaureates ln
  ON REPLACE((pr.paperid)::text, '"', '') = ln.paperid


LEFT JOIN link_patents lp
  ON REPLACE((pr.paperid)::text, '"', '') = lp.paperid;