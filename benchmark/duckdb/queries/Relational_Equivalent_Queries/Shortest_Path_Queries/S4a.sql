-- Relational equivalent of S4a; recursive edge joins, no shortest-path syntax.
WITH RECURSIVE reach(institutionid, depth, visited) AS (
    SELECT a.institutionid, 0, LIST_VALUE(CAST(a.institutionid AS VARCHAR))
    FROM Affiliations a
    WHERE a.institutionid = 'I4210136388'
    UNION ALL
    SELECT e.associated_institution_id, r.depth + 1, list_append(r.visited, CAST(e.associated_institution_id AS VARCHAR))
    FROM reach r
    JOIN affl_assoc_affl e ON e.institution_id = r.institutionid
    WHERE NOT list_contains(r.visited, e.associated_institution_id)
)
SELECT MIN(a.institutionid) AS inst_for_institutionid
FROM reach r
JOIN Affiliations a ON a.institutionid = r.institutionid
WHERE r.depth >= 0
  AND a.productivity > 8000;
