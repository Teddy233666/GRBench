MATCH (paper:Papers)
WHERE paper.paperid = 'W4211259235'
  AND paper.citation_count < 5
RETURN count(paper.paperid) AS matched_count,
       min(paper.paperid) AS min_ref_paperid;
