MATCH p = (paper:Papers)-[:PaperReferences]->(ref:Papers)
WHERE paper.paperid = 'W4211259235'
  AND ref.citation_count < 150
RETURN count(ref.paperid) AS matched_count,
       min(ref.paperid) AS min_ref_paperid;
