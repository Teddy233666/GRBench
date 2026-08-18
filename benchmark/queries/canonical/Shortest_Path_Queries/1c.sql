SELECT MIN(g.inst_asia_institutionid)
FROM GRAPH_TABLE(
    sciscinet_graph
    MATCH
        p = ANY SHORTEST
        (inst_0 IS Affiliations)
            -[af IS affl_assoc_affl]->{1,}
        (inst_asia IS Affiliations)
    WHERE
         inst_0.institutionid = 'I4210136388'
        AND inst_asia.institutionid='I4210088668'
    COLUMNS (
        inst_0.institutionid AS  inst_0_institutionid,
        inst_asia.institutionid AS   inst_asia_institutionid
    )
)g;
