
SELECT
     MIN(assoc.institutionid)     AS associated_institutionid
FROM GRAPH_TABLE(
    sciscinet_graph
    MATCH
       (inst IS Affiliations)
            -[r1 IS affl_assoc_affl]->
        (m1 IS Affiliations)
            -[r2 IS affl_assoc_affl]->
        (m2 IS Affiliations)
            -[r3 IS affl_assoc_affl]->
        (m3 IS Affiliations)
            -[r4 IS affl_assoc_affl]->
        (assoc IS Affiliations)
  WHERE inst.institutionid LIKE 'I42101230%'
        AND m2.h_index  >= 1000
    COLUMNS(
        inst.institutionid   AS institutionid,
        assoc.institutionid  AS associated_institutionid
    )
) assoc;