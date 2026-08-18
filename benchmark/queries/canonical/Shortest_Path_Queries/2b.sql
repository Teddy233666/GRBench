SELECT MIN(g.inst_eu_institutionid)
FROM GRAPH_TABLE(
    sciscinet_graph
    MATCH
        p = ANY SHORTEST
        (inst_0 IS Affiliations)
            -[af IS affl_assoc_affl]->{1,3}
        (inst_eu IS Affiliations)
    WHERE
         inst_0.institutionid = 'I4210136388'
        AND inst_eu.productivity>48000
    COLUMNS (
        inst_0.institutionid AS  inst_0_institutionid,
        inst_eu.institutionid AS   inst_eu_institutionid
    )
)g;
