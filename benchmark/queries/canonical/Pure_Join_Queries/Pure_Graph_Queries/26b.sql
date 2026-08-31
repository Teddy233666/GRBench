SELECT
    MIN(p.paperid) AS cited_paperid
FROM Papers p
JOIN Link_NIH ln
    ON p.paperid = ln.paperid
JOIN NIH_Metadata n
    ON ln.paperid = n.paperid
WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 1;