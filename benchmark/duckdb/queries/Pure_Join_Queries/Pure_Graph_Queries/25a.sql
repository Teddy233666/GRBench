SELECT
    MIN(inst0.institutionid) AS inst_0_institutionid
FROM Affiliations inst0
JOIN affl_assoc_affl af1
    ON inst0.institutionid = af1.institution_id
JOIN Affiliations inst1
    ON af1.associated_institution_id = inst1.institutionid
JOIN affl_assoc_affl af2
    ON inst1.institutionid = af2.institution_id
JOIN Affiliations inst2
    ON af2.associated_institution_id = inst2.institutionid
JOIN affl_assoc_affl af3
    ON inst2.institutionid = af3.institution_id
JOIN Affiliations inst3
    ON af3.associated_institution_id = inst3.institutionid
WHERE inst0.institutionid LIKE 'I42101230%';