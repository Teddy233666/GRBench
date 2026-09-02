MATCH (p:Papers)
MATCH (ln:link_nih)
MATCH (n_nih:nih_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count = 1 AND ln.paperid = p.paperid AND n_nih.award_id = ln.award_id
OPTIONAL MATCH (ls:link_nsf) WHERE ls.paperid = p.paperid
OPTIONAL MATCH (n_nsf:nsf_metadata) WHERE n_nsf.award_id = ls.award_id
RETURN MIN(p.paperid) AS paperid, MIN(CASE WHEN n_nsf IS NULL THEN NULL ELSE n_nsf.award_id END) AS award_id;
