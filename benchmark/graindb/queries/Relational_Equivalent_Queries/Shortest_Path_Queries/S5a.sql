-- Relational equivalent of S5a; recursive edge joins, no shortest-path syntax.
WITH RECURSIVE walk(paperid, depth, visited) AS (
    SELECT p.paperid, 0, LIST_VALUE(CAST(p.paperid AS VARCHAR))
    FROM Papers p
    WHERE p.paperid = 'W4211259235'
    UNION ALL
    SELECT e.cited_paperid, w.depth + 1, list_append(w.visited, CAST(e.cited_paperid AS VARCHAR))
    FROM walk w
    JOIN PaperReferences e ON e.citing_paperid = w.paperid
    WHERE w.depth < 1
      AND NOT list_contains(w.visited, e.cited_paperid)
)
SELECT MIN(p.paperid) AS ref_paperid
FROM walk w
JOIN Papers p ON p.paperid = w.paperid
WHERE p.citation_count < 150;
