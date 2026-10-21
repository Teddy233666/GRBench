-- Relational equivalent of S5a; recursive edge joins, no shortest-path syntax.
WITH RECURSIVE walk(paperid, depth, visited) AS (
    SELECT p.paperid, 0, ARRAY[p.paperid]::text[]
    FROM Papers p
    WHERE p.paperid = 'W4211259235'
    UNION ALL
    SELECT e.cited_paperid, w.depth + 1, w.visited || e.cited_paperid
    FROM walk w
    JOIN PaperReferences e ON e.citing_paperid = w.paperid
    WHERE w.depth < 1
      AND NOT e.cited_paperid = ANY(w.visited)
)
SELECT MIN(p.paperid) AS ref_paperid
FROM walk w
JOIN Papers p ON p.paperid = w.paperid
WHERE p.citation_count < 150;
