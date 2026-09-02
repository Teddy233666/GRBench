SELECT
    MIN(pn.paperid::text)            AS cited_paperid,
    MIN(ln.laureate_id::text) AS minNobel
FROM

cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_ClinicalTrials]->(n:clinicaltrials_metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND toInteger(p.citation_count) =1
    RETURN p.paperid
$$) AS pn(paperid agtype)

LEFT JOIN link_nobellaureates ln
  ON pn.paperid::text = ln.paperid;