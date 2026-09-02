MATCH (p4:Papers)
MATCH (p4)-[r:PaperReferences]->(ref:Papers)
WHERE p4.paperid = 'W4211259235' AND ref.citation_count < 5
OPTIONAL MATCH (lnsf:link_nsf) WHERE lnsf.paperid = p4.paperid
OPTIONAL MATCH (nsf:nsf_metadata) WHERE nsf.award_id = lnsf.award_id
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p4.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = ref.paperid
RETURN MIN(p4.paperid) AS minPaper, MIN(CASE WHEN nsf IS NULL THEN NULL ELSE nsf.award_id END) AS award_id, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
