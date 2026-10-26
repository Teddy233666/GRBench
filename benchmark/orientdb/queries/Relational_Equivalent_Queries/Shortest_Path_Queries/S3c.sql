SELECT MIN(institution_id) AS institutionid
FROM contributed_from
WHERE institution_id IN (
    SELECT institutionid FROM (TRAVERSE out('affl_assoc_affl') FROM (SELECT FROM Affiliations WHERE institutionid = 'I4210136388') MAXDEPTH 4)
    WHERE @class = 'Affiliations' AND institutionid = 'I4210088668'
);
