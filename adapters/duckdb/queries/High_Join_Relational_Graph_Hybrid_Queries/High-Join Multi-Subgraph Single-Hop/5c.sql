SELECT
    MIN(ref.paper_id) AS minPaper,
    MIN(nsf.award_id) AS award_id,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
GRAPH_TABLE(
    sciscinet_graph
    MATCH (p4 IS Papers)-[r3 IS PaperReferences]->(ref IS Papers)
    WHERE p4.paperid='W4211259235'
    AND ref.citation_count<5
    COLUMNS(
        p4.paperid AS paper_id,
        ref.paperid AS ref_paper_id,
        ref.citation_count AS citation_count
    )

) ref
LEFT JOIN GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (p2 IS Papers)
            -[ln IS Link_NSF]->
        (n IS NSF_Metadata)

    COLUMNS(
        p2.paperid            AS paper_id,
        n.award_id            AS award_id,
        n.type_crossref  AS funder_name
    )
) nsf
ON ref.paper_id = nsf.paper_id
LEFT JOIN papersources ps
  ON ref.ref_paper_id = ps.paperid
LEFT JOIN sources s
  ON ps.sourceid = s.sourceid
LEFT JOIN link_nobellaureates ln
  ON ref.paper_id  = ln.paperid
LEFT JOIN link_patents lp
  ON ref.ref_paper_id  = lp.paperid;
