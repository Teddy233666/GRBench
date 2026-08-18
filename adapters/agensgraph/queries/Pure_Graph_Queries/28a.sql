SELECT
    MIN(REPLACE((ref.ref_paper_id)::text, '"', '')),
    MIN(REPLACE((nsf.award_id)::text, '"', ''))
FROM
(
    MATCH (p4:Papers)-[r1:PaperReferences]->(ref:Papers)
    WHERE p4.paperid STARTS WITH 'W423590139'
      AND p4.citation_count <= 3
    RETURN
        p4.paperid  AS paper_id,
        ref.paperid AS ref_paper_id
) ref

LEFT JOIN
(
    MATCH (p2:Papers)-[ln:Link_NSF]->(n:NSF_Metadata)
    RETURN
        p2.paperid      AS paper_id,
        n.award_id      AS award_id,
        n.type_crossref AS funder_name
) nsf
ON REPLACE((ref.paper_id)::text, '"', '') = REPLACE((nsf.paper_id)::text, '"', '');