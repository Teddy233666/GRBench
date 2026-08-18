SELECT
    MIN(REPLACE((g_ref.paperid)::text, '"', '')) AS minPaper,
    MIN(REPLACE((g_ap.authorid)::text, '"', '')) AS minAuthor,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
    MATCH (p:Papers)-[r1:PaperReferences]->(ref:Papers)
     WHERE p.paperid='W4211259235'
     AND ref.citation_count<5
    RETURN
        p.paperid   AS paperid,
        ref.paperid AS ref_paperid
) g_ref


LEFT JOIN
(
    MATCH (a:Authors_Gender)-[ap:Authors_Paper]->(p:Papers)
    WHERE a.h_index>80
    RETURN
        a.authorid AS authorid,
        p.paperid  AS paperid
) g_ap
ON REPLACE((g_ap.paperid)::text, '"', '') = REPLACE((g_ref.paperid)::text, '"', '')


LEFT JOIN link_nobellaureates ln
  ON REPLACE((g_ref.paperid)::text, '"', '') = ln.paperid


LEFT JOIN author_details ad
  ON REPLACE((g_ap.authorid)::text, '"', '') = ad.authorid;
