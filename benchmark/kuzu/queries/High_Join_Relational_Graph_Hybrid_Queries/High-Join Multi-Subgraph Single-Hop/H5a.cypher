MATCH (p:Papers)
MATCH (p)-[r1:PaperReferences]->(ref:Papers)
WHERE p.paperid = 'W4211259235' AND ref.citation_count < 150
OPTIONAL MATCH (lnsf:link_nsf) WHERE lnsf.paperid = p.paperid
OPTIONAL MATCH (nsf:nsf_metadata) WHERE nsf.award_id = lnsf.award_id
OPTIONAL MATCH (ref)-[ps:papersources]->(s:Sources)
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = ref.paperid
RETURN MIN(p.paperid) AS minPaper, MIN(CASE WHEN nsf IS NULL THEN NULL ELSE nsf.award_id END) AS award_id, MIN(CASE WHEN s IS NULL THEN NULL ELSE s.sourceid END) AS minSource, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
