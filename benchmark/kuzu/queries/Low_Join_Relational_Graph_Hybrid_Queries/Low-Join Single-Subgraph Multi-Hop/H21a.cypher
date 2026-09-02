MATCH (orig:Papers)
MATCH (orig)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(cited:Papers)
WHERE orig.paperid = 'W2122344208' AND cited.citation_count < 150
OPTIONAL MATCH (h0:hit_papers_level0) WHERE h0.paperid = orig.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = cited.paperid
RETURN MIN(orig.paperid) AS cited_paperid, MIN(CASE WHEN h0 IS NULL THEN NULL ELSE h0.fieldid END) AS fieldid, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
