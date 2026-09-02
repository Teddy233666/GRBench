SELECT
    MIN(tri.inst_0_institutionid)
FROM GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (inst0 IS Affiliations)
            -[af1 IS affl_assoc_affl]->
        (inst1 IS Affiliations)
         -[af2 IS affl_assoc_affl]->
        (inst2 IS Affiliations)
         -[af3 IS affl_assoc_affl]->
        (inst3 IS Affiliations)
    WHERE inst0.institutionid LIKE 'I42101230%'
            AND inst3.h_index  >=1500
    COLUMNS(
       inst0.institutionid AS inst_0_institutionid
    )
) tri;
