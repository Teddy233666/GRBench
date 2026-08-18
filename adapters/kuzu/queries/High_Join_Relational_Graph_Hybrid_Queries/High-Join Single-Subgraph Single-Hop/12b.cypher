MATCH (p:Papers)
MATCH (lct:link_clinicaltrials)
MATCH (cm:clinicaltrials_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count <= 1 AND lct.paperid = p.paperid AND cm.nct_id = lct.nct_id
OPTIONAL MATCH (p)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (h1:hit_papers_level1) WHERE h1.paperid = p.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p.paperid
RETURN MIN(p.paperid) AS cited_paperid, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN h1 IS NULL THEN NULL ELSE h1.paperid END) AS minh1paperid, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
