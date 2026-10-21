-- Relational equivalent of S3a; recursive edge joins plus a relational LEFT JOIN.
WITH RECURSIVE reach(institutionid, depth, visited) AS (
    SELECT a.institutionid, 0, ARRAY[a.institutionid]::text[]
    FROM Affiliations a
    WHERE a.institutionid = 'I4210136388'
    UNION ALL
    SELECT e.associated_institution_id, r.depth + 1, r.visited || e.associated_institution_id
    FROM reach r
    JOIN affl_assoc_affl e ON e.institution_id = r.institutionid
    WHERE NOT e.associated_institution_id = ANY(r.visited)
      AND r.depth < 4
), endpoints AS (
    SELECT DISTINCT a.institutionid
    FROM reach r
    JOIN Affiliations a ON a.institutionid = r.institutionid
    WHERE r.depth >= 1 AND a.productivity > 8000
)
SELECT MIN(cf.institution_id) AS institutionid
FROM endpoints e
LEFT JOIN contributed_from cf ON cf.institution_id = e.institutionid;
