MATCH (p4:Papers)
MATCH (p4)-[r1:PaperReferences]->(ref:Papers)
WHERE p4.paperid STARTS WITH 'W423590139' AND p4.citation_count <= 3
OPTIONAL MATCH (ln:link_nsf) WHERE ln.paperid = p4.paperid
OPTIONAL MATCH (nsf:nsf_metadata) WHERE nsf.award_id = ln.award_id
RETURN MIN(ref.paperid) AS min_ref_paper_id, MIN(CASE WHEN nsf IS NULL THEN NULL ELSE nsf.award_id END) AS award_id;
