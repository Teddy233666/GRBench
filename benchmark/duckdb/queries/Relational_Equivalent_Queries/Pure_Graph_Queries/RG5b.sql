SELECT
    MIN(assoc.institutionid) AS associated_institutionid
FROM Affiliations inst
JOIN affl_assoc_affl r1
    ON inst.institutionid = r1.institution_id
JOIN Affiliations m1
    ON r1.associated_institution_id = m1.institutionid
JOIN affl_assoc_affl r2
    ON m1.institutionid = r2.institution_id
JOIN Affiliations m2
    ON r2.associated_institution_id = m2.institutionid
JOIN affl_assoc_affl r3
    ON m2.institutionid = r3.institution_id
JOIN Affiliations m3
    ON r3.associated_institution_id = m3.institutionid
JOIN affl_assoc_affl r4
    ON m3.institutionid = r4.institution_id
JOIN Affiliations assoc
    ON r4.associated_institution_id = assoc.institutionid
WHERE inst.institutionid LIKE 'I42101230%'
  AND m2.h_index >= 1000;