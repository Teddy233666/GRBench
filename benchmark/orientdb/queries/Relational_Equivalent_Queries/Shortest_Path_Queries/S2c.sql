SELECT MIN(institutionid) AS inst_asia_institutionid
FROM (TRAVERSE out('affl_assoc_affl') FROM (SELECT FROM Affiliations WHERE institutionid = 'I4210136388') MAXDEPTH 3)
WHERE @class = 'Affiliations'
  AND $depth >= 1
  AND institutionid = 'I4210088668';
