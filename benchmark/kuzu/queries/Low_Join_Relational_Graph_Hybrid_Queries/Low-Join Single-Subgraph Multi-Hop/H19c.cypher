MATCH (orig:Papers)
MATCH (orig)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(cited:Papers)
WHERE orig.paperid = 'W2122344208' AND cited.citation_count<5
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = cited.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = orig.paperid
RETURN MIN(orig.paperid) AS cited_paperid, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
