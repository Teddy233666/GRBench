MATCH (p:Papers)
MATCH (lnsf:link_nsf)
MATCH (nsf:nsf_metadata)
WHERE p.paperid STARTS WITH 'W423590139' AND p.citation_count = 1 AND lnsf.paperid = p.paperid AND nsf.award_id = lnsf.award_id
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p.paperid
RETURN MIN(p.paperid) AS cited_paperid, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
