SELECT MIN(institutionid) AS institutionid
FROM Affiliations
WHERE productivity > 8000
  AND shortestPath((SELECT FROM Affiliations WHERE institutionid = 'I4210136388'), @rid, 'OUT', 'affl_assoc_affl').size() > 0;
