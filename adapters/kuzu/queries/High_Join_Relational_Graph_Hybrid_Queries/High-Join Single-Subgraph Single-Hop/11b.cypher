MATCH (p:Papers)
MATCH (lnsf:link_nsf)
MATCH (nm:nsf_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count <= 1 AND lnsf.paperid = p.paperid AND nm.award_id = lnsf.award_id
OPTIONAL MATCH (p)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (h0:hit_papers_level0) WHERE h0.paperid = p.paperid
RETURN MIN(p.paperid) AS cited_paperid, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN h0 IS NULL THEN NULL ELSE h0.paperid END) AS minh0paperid;
