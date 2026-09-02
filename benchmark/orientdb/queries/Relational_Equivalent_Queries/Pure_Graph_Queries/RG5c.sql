SELECT
    $q0[0].v AS associated_institutionid
LET
    $q0 = (SELECT MIN(institutionid) AS v FROM Affiliations WHERE institutionid IN (SELECT associated_institution_id FROM affl_assoc_affl WHERE institution_id IN (SELECT institutionid FROM Affiliations WHERE institutionid IN (SELECT associated_institution_id FROM affl_assoc_affl WHERE institution_id IN (SELECT institutionid FROM Affiliations WHERE h_index >= 1500 AND institutionid IN (SELECT associated_institution_id FROM affl_assoc_affl WHERE institution_id IN (SELECT institutionid FROM Affiliations WHERE institutionid IN (SELECT associated_institution_id FROM affl_assoc_affl WHERE institution_id IN (SELECT institutionid FROM Affiliations WHERE institutionid LIKE 'I42101230%')))))))));
