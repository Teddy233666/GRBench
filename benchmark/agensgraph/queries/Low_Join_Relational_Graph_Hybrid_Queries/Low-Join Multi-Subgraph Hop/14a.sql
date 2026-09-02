SELECT
    MIN(REPLACE((ref.paper_id)::text, '"', '')) AS minPaper,
    MIN(REPLACE((ap.author_id)::text, '"', '')) AS minAuthor1,
    MIN(REPLACE((nsf.award_id)::text, '"', '')) AS award_id,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
    MATCH (p4:Papers)-[r1:PaperReferences]->(p5:Papers)
          -[r2:PaperReferences]->(p6:Papers)
          -[r3:PaperReferences]->(ref:Papers)
    WHERE p4.paperid='W2122344208'
    AND ref.citation_count<150
    RETURN
        p4.paperid  AS paper_id,
        ref.paperid AS ref_paper_id
) ref


LEFT JOIN
(
    MATCH (a:Authors_Gender)-[ap_rel:Authors_Paper]->(p:Papers)
    WHERE a.h_index>10
    RETURN
        a.authorid       AS author_id,
        a.display_name   AS author_name,
        p.paperid        AS paper_id,
        p.year           AS paper_year,
        p.citation_count AS citations
) ap
ON REPLACE((ap.paper_id)::text, '"', '') = REPLACE((ref.ref_paper_id)::text, '"', '')


LEFT JOIN
(
    MATCH (p2:Papers)-[ln:Link_NSF]->(n:NSF_Metadata)
    RETURN
        p2.paperid        AS paper_id,
        n.award_id        AS award_id,
        n.type_crossref   AS funder_name
) nsf
ON REPLACE((ref.paper_id)::text, '"', '') = REPLACE((nsf.paper_id)::text, '"', '')


LEFT JOIN link_nobellaureates ln
  ON REPLACE((ref.paper_id)::text, '"', '') = ln.paperid


LEFT JOIN author_details ad
  ON REPLACE((ap.author_id)::text, '"', '') = ad.authorid;