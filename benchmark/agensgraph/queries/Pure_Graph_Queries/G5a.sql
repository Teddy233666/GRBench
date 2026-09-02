SELECT
    MIN(REPLACE((assoc.associated_institutionid)::text, '"', '')) AS associated_institutionidS associated_institutionid
FROM
(
    MATCH (inst:Affiliations)-[r1:affl_assoc_affl]->(m1:Affiliations)
          -[r2:affl_assoc_affl]->(m2:Affiliations)
          -[r3:affl_assoc_affl]->(m3:Affiliations)
          -[r4:affl_assoc_affl]->(assoc:Affiliations)
    WHERE inst.institutionid STARTS WITH 'I42101230'
    RETURN
        inst.institutionid   AS institutionid,
        assoc.institutionid  AS associated_institutionid
) assoc;