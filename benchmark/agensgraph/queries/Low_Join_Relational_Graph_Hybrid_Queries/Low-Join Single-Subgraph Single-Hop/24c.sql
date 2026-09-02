SELECT
    MIN(REPLACE((pn.paperid)::text, '"', '')),
    MIN(ln.laureate_id) AS minNobel
FROM
(
    MATCH (p:Papers)-[pr:Link_ClinicalTrials]->(n:clinicaltrials_metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND p.citation_count = 1
    RETURN
        p.paperid AS paperid
) pn

JOIN link_nobellaureates ln
  ON REPLACE((pn.paperid)::text, '"', '') = ln.paperid;