MATCH (p1:Papers)
MATCH (p1)-[r1:PaperReferences]->(p2:Papers)
MATCH (p2)-[r2:PaperReferences]->(p3:Papers)
MATCH (p3)-[r3:PaperReferences]->(p4:Papers)
WHERE p1.paperid = 'W2122344208' AND p4.citation_count < 5
OPTIONAL MATCH (h0:hit_papers_level0) WHERE h0.paperid = p1.paperid
OPTIONAL MATCH (h1:hit_papers_level1) WHERE h1.paperid = p1.paperid
OPTIONAL MATCH (ln:link_nobellaureates) WHERE ln.paperid = p4.paperid
OPTIONAL MATCH (lp:link_patents) WHERE lp.paperid = p4.paperid
RETURN MIN(p1.paperid) AS cited_paperid, MIN(CASE WHEN h0 IS NULL THEN NULL ELSE h0.fieldid END) AS fieldid0, MIN(CASE WHEN h1 IS NULL THEN NULL ELSE h1.fieldid END) AS fieldid1, MIN(CASE WHEN ln IS NULL THEN NULL ELSE ln.laureate_id END) AS minNobel, MIN(CASE WHEN lp IS NULL THEN NULL ELSE lp.patent END) AS minPatent;
