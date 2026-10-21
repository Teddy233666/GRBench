-- Relational equivalent of S1c; OrientDB uses TRAVERSE for the recursive closure.
SELECT MIN(institutionid) AS inst_asia_institutionid
FROM (TRAVERSE out('affl_assoc_affl') FROM (SELECT FROM Affiliations WHERE institutionid = 'I4210136388')) v
WHERE @class = 'Affiliations'
  AND $depth >= 1
  AND v.institutionid = 'I4210088668';
