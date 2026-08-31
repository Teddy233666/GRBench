SELECT
    MIN(ref.paper_id) AS minPaper,
    MIN(ap.author_id) AS minAuthor1,
    MIN(nsf.award_id) AS award_id,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minAuthorid2
FROM
GRAPH_TABLE(
    sciscinet_graph
     MATCH (p4 IS Papers)-[r1 IS PaperReferences]->(p5 IS Papers)-[r2 IS PaperReferences]->(p6 IS Papers)-[r3 IS PaperReferences]->(ref IS Papers)
    WHERE p4.paperid='W2122344208'
    AND ref.citation_count<80
    COLUMNS(
        p4.paperid AS paper_id,
        ref.paperid AS ref_paper_id,
        ref.citation_count AS citation_count
    )

) ref
LEFT JOIN
GRAPH_TABLE(
    sciscinet_graph
    MATCH
        (a IS Authors_Gender)
            -[ap_rel IS Authors_Paper]->
        (p IS Papers)
    WHERE a.h_index>30
    COLUMNS(
        a.authorid       AS author_id,
        a.display_name   AS author_name,
        p.paperid        AS paper_id,
        p.year           AS paper_year,
        p.citation_count AS citations
    )
) ap
ON ap.paper_id = ref.ref_paper_id
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
LEFT JOIN link_nobellaureates ln
  ON ref.paper_id  = ln.paperid
LEFT JOIN author_details ad
  ON ap.author_id = ad.authorid;
