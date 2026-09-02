MATCH (p:Papers {paperid:'W4211259235'})
MATCH path = allshortestpaths((p)-[r1:PaperReferences*0..1]->(ref:Papers))
WHERE ref.citation_count < 80
RETURN MIN(ref.paperid) AS ref_paperid;
