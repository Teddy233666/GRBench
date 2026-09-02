SELECT
    $q0[0].v AS associated_institutionid
LET
    $q0 = (SELECT MIN(associated_institutionid) AS v
FROM (
    MATCH {class:Affiliations, as:inst, where:(institutionid LIKE 'I42101230%')}.out('affl_assoc_affl'){class:Affiliations, as:m1}.out('affl_assoc_affl'){class:Affiliations, as:m2, where:(h_index >= 1500)}.out('affl_assoc_affl'){class:Affiliations, as:m3}.out('affl_assoc_affl'){class:Affiliations, as:assoc} RETURN assoc.institutionid AS associated_institutionid
));
