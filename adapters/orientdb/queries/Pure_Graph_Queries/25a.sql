SELECT
    $q0[0].v AS inst_0_institutionid
LET
    $q0 = (SELECT MIN(inst_0_institutionid) AS v
FROM (
    MATCH {class:Affiliations, as:inst0, where:(institutionid LIKE 'I42101230%')}.out('affl_assoc_affl'){class:Affiliations, as:inst1}.out('affl_assoc_affl'){class:Affiliations, as:inst2}.out('affl_assoc_affl'){class:Affiliations, as:inst3} RETURN inst0.institutionid AS inst_0_institutionid
));
