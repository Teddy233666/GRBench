SELECT
     MIN(REPLACE((tri.inst_0_institutionid)::text, '"', ''))
FROM
(
    MATCH (inst0:Affiliations)-[af1:affl_assoc_affl]->(inst1:Affiliations)
          -[af2:affl_assoc_affl]->(inst2:Affiliations)
          -[af3:affl_assoc_affl]->(inst3:Affiliations)
    WHERE inst0.institutionid STARTS WITH 'I42101230'
      AND inst2.h_index  >= 1500
    RETURN
        inst0.institutionid AS inst_0_institutionid
) tri;
