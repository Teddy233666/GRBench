-- GrainDB-compatible explicit bounded relational expansion for S3b.
WITH reach AS (
    SELECT a.institutionid AS institutionid, 0 AS depth FROM Affiliations a WHERE a.institutionid = 'I4210136388'
    UNION
    SELECT e1.associated_institution_id, 1 FROM affl_assoc_affl e1 WHERE e1.institution_id = 'I4210136388'
    UNION
    SELECT e2.associated_institution_id, 2 FROM affl_assoc_affl e1 JOIN affl_assoc_affl e2 ON e2.institution_id=e1.associated_institution_id WHERE e1.institution_id='I4210136388' AND e2.associated_institution_id NOT IN ('I4210136388', e1.associated_institution_id)
    UNION
    SELECT e3.associated_institution_id, 3 FROM affl_assoc_affl e1 JOIN affl_assoc_affl e2 ON e2.institution_id=e1.associated_institution_id JOIN affl_assoc_affl e3 ON e3.institution_id=e2.associated_institution_id WHERE e1.institution_id='I4210136388' AND e2.associated_institution_id NOT IN ('I4210136388',e1.institution_id) AND e3.associated_institution_id NOT IN ('I4210136388',e1.associated_institution_id,e2.associated_institution_id)
    UNION
    SELECT e4.associated_institution_id, 4 FROM affl_assoc_affl e1 JOIN affl_assoc_affl e2 ON e2.institution_id=e1.associated_institution_id JOIN affl_assoc_affl e3 ON e3.institution_id=e2.associated_institution_id JOIN affl_assoc_affl e4 ON e4.institution_id=e3.associated_institution_id WHERE e1.institution_id='I4210136388' AND e2.associated_institution_id NOT IN ('I4210136388',e1.associated_institution_id) AND e3.associated_institution_id NOT IN ('I4210136388',e1.associated_institution_id,e2.associated_institution_id) AND e4.associated_institution_id NOT IN ('I4210136388',e1.associated_institution_id,e2.associated_institution_id,e3.associated_institution_id)
)
SELECT MIN(cf.institutionid) AS institutionid
FROM reach r JOIN Affiliations a ON a.institutionid=r.institutionid LEFT JOIN contributed_from cf ON cf.institutionid=a.institutionid
WHERE r.depth >= 1 AND a.productivity > 48000;
