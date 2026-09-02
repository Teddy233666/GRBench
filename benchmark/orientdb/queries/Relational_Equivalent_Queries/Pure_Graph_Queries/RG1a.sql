SELECT
    $q0[0].v AS inst_0_institutionid
LET
    $q0 = (SELECT MIN(institutionid) AS v FROM Affiliations WHERE institutionid LIKE 'I42101230%' AND institutionid IN (SELECT institution_id FROM affl_assoc_affl WHERE associated_institution_id IN (SELECT institutionid FROM Affiliations WHERE institutionid IN (SELECT institution_id FROM affl_assoc_affl WHERE associated_institution_id IN (SELECT institutionid FROM Affiliations WHERE institutionid IN (SELECT institution_id FROM affl_assoc_affl WHERE associated_institution_id IN (SELECT institutionid FROM Affiliations)))))));
