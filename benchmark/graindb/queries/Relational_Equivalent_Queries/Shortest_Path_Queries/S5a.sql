-- GrainDB-compatible bounded relational expansion for S5a.
WITH walk AS (
    SELECT p.paperid AS paperid, 0 AS depth FROM Papers p WHERE p.paperid = 'W4211259235'
    UNION
    SELECT e.cited_paperid, 1 FROM PaperReferences e WHERE e.citing_paperid = 'W4211259235'
)
SELECT MIN(p.paperid) AS ref_paperid
FROM walk w JOIN Papers p ON p.paperid=w.paperid
WHERE p.citation_count < 150;
