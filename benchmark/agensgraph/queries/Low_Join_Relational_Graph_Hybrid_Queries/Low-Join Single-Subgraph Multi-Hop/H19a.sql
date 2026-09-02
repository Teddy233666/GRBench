SELECT
    MIN(REPLACE((pr.paperid)::text, '"', '')) AS cited_paperid,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
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


LEFT JOIN link_nobellaureates ln
  ON REPLACE((pr.paperid)::text, '"', '') = ln.paperid


LEFT JOIN link_patents lp
  ON REPLACE((pr.cited_paperid)::text, '"', '') = lp.paperid;