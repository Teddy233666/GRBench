SELECT
    MIN(ref.ref_paper_id),
    MIN(nsf.award_id)
FROM
GRAPH_TABLE(
    sciscinet_graph
     MATCH (p4 IS Papers)-[r1 IS PaperReferences]->(ref IS Papers)
     WHERE p4.paperid LIKE 'W423590139%'
      AND p4.citation_count <=1
    COLUMNS(
        p4.paperid AS paper_id,
        ref.paperid AS ref_paper_id
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
ON ref.paper_id = nsf.paper_id;