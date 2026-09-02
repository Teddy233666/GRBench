SELECT MIN(institutionid) AS institutionid
FROM Affiliations
WHERE institutionid = 'I4210088668'
  AND shortestPath((SELECT FROM Affiliations WHERE institutionid = 'I4210136388'), @rid, 'OUT', 'affl_assoc_affl').size() BETWEEN 2 AND 4;
