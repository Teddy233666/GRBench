MATCH (p:Papers)
MATCH (ln:link_nsf)
MATCH (n:nsf_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count = 1 AND ln.paperid = p.paperid AND n.award_id = ln.award_id
RETURN MIN(p.paperid) AS cited_paperid;
