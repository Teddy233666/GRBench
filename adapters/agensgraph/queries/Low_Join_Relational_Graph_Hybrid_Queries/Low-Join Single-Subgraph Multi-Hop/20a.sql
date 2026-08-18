SELECT
    MIN(REPLACE((pr.paperid)::text, '"', '')) AS cited_paperid,
    MIN(src_table.sourceid) AS minSource
FROM
(
    MATCH (orig:Papers)-[r1:PaperReferences]->(p2:Papers)
          -[r2:PaperReferences]->(p3:Papers)
          -[r3:PaperReferences]->(cited:Papers)
    WHERE orig.paperid='W2122344208'
    AND cited.citation_count<150
    RETURN
        orig.paperid AS paperid,
        cited.paperid AS cited_paperid
) pr


LEFT JOIN papersources ps_table
  ON REPLACE((pr.paperid)::text, '"', '') = ps_table.paperid


LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid;