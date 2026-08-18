MATCH (p:Papers)
MATCH (lnih:link_nih)
MATCH (nih:nih_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count <= 1 AND lnih.paperid = p.paperid AND nih.award_id = lnih.award_id
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
RETURN MIN(p.paperid) AS cited_paperid, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel;
