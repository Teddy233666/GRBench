SELECT
    MIN(REPLACE((g_ref.paperid)::text, '"', '')),
    MIN(REPLACE((g_ap.award_id)::text, '"', ''))
FROM
(
    MATCH (p:Papers)-[pr:Link_NIH]->(n:NIH_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND p.citation_count <= 3
    RETURN
        p.paperid AS paperid
) g_ref

LEFT JOIN
(
    MATCH (p:Papers)-[pr:Link_NSF]->(n:NSF_Metadata)
    RETURN
        p.paperid AS paperid,
        n.award_id AS award_id
) g_ap
ON REPLACE((g_ap.paperid)::text, '"', '') = REPLACE((g_ref.paperid)::text, '"', '');