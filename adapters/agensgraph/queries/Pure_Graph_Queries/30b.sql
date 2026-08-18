SELECT
 MIN(REPLACE((pn.paperid)::text, '"', '')) AS cited_paperid
FROM
(
    MATCH (p:Papers)-[pr:Link_NSF]->(n:NSF_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND p.citation_count <= 1
    RETURN
        p.paperid AS paperid
) pn;