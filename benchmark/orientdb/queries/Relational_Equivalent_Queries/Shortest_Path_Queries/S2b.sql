-- Relational equivalent of S2b; OrientDB uses TRAVERSE for the recursive closure.
SELECT MIN(institutionid) AS inst_eu_institutionid
FROM (TRAVERSE out('affl_assoc_affl') FROM (SELECT FROM Affiliations WHERE institutionid = 'I4210136388') MAXDEPTH 3) v
WHERE @class = 'Affiliations'
  AND $depth >= 1
  AND v.productivity > 48000;
