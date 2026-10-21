-- Relational equivalent of S3a; OrientDB uses TRAVERSE for the recursive closure.
SELECT MIN(cf.institution_id) AS institutionid
FROM contributed_from cf
WHERE cf.institution_id IN (
    SELECT institutionid FROM (TRAVERSE out('affl_assoc_affl') FROM (SELECT FROM Affiliations WHERE institutionid = 'I4210136388') MAXDEPTH 4)
    WHERE @class = 'Affiliations' AND v.productivity > 8000
);
