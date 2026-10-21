-- Relational equivalent of S2a; OrientDB uses TRAVERSE for the recursive closure.
SELECT MIN(institutionid) AS inst_for_institutionid
FROM (TRAVERSE out('affl_assoc_affl') FROM (SELECT FROM Affiliations WHERE institutionid = 'I4210136388') MAXDEPTH 3) v
WHERE @class = 'Affiliations'
  AND $depth >= 1
  AND v.productivity > 8000;
