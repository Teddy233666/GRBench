MATCH (p:Papers)
MATCH (lct:link_clinicaltrials)
MATCH (ct:clinicaltrials_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count <= 3 AND lct.paperid = p.paperid AND ct.nct_id = lct.nct_id
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
RETURN MIN(p.paperid) AS cited_paperid, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel;
