MATCH (p:Papers)
MATCH (lnih:link_nih)
MATCH (nm:nih_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count <= 3 AND lnih.paperid = p.paperid AND nm.award_id = lnih.award_id
OPTIONAL MATCH (p)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p.paperid
RETURN MIN(p.paperid) AS cited_paperid, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
