SELECT MIN(g.inst_for_institutionid)
FROM GRAPH_TABLE(
    sciscinet_graph
    MATCH
        p = ANY SHORTEST
        (inst_cn IS Affiliations)
            -[af IS affl_assoc_affl]->{1,3}
        (inst_for IS Affiliations)
    WHERE
        inst_cn.institutionid = 'I4210136388'
        AND inst_for.productivity>8000
    COLUMNS (
        inst_cn.institutionid AS  inst_cn_institutionid,
        inst_for.institutionid AS inst_for_institutionid
    )
)g;