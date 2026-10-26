-- Relational equivalent of S2c; recursive edge joins, no shortest-path syntax.
WITH RECURSIVE reach(institutionid, depth, visited) AS (
    SELECT a.institutionid, 0, ARRAY[a.institutionid]::text[]
    FROM affiliations_profile a
    WHERE a.institutionid = 'I4210136388'
    UNION ALL
    SELECT e.associated_institution_id, r.depth + 1, r.visited || e.associated_institution_id
    FROM reach r
    JOIN affl_assoc_affl_profile e ON e.institution_id = r.institutionid
    WHERE NOT e.associated_institution_id = ANY(r.visited)
      AND r.depth < 3
)
SELECT MIN(a.institutionid) AS inst_asia_institutionid
FROM reach r
JOIN affiliations_profile a ON a.institutionid = r.institutionid
WHERE r.depth >= 1
  AND a.institutionid = 'I4210088668';
