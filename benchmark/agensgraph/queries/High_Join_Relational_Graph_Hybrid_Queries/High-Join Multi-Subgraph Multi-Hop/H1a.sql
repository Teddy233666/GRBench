SELECT
    MIN(REPLACE(g_ref.paperid::text, '"', '')) AS minPaper,
    MIN(REPLACE(g_ap.authorid::text, '"', '')) AS minAuthor,
    MIN(REPLACE(g_cf.paperid::text, '"', '')) AS minAff,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
    MATCH (p:Papers)-[r1:PaperReferences]->(p1:Papers)-[r2:PaperReferences]->(p2:Papers)-[r3:PaperReferences]->(ref:Papers)
    WHERE p.paperid='W2122344208'
    AND ref.citation_count<150
    RETURN
        p.paperid  AS paperid,
        ref.paperid AS ref_paperid
) g_ref
LEFT JOIN (
    MATCH (a:Authors_Gender)-[ap:Authors_Paper]->(p:Papers)
    WHERE a.h_index>10
    RETURN
        a.authorid     AS authorid,
        p.paperid      AS paperid
) g_ap
ON REPLACE(g_ap.paperid::text, '"', '') = REPLACE(g_ref.paperid::text, '"', '')

LEFT JOIN (
    MATCH (p:Papers)-[cf:contributed_from]->(inst:Affiliations)
    WHERE inst.productivity>1000
    RETURN
        p.paperid AS paperid
) g_cf
ON REPLACE(g_ref.ref_paperid::text, '"', '') = REPLACE(g_cf.paperid::text, '"', '')

LEFT JOIN papersources ps
  ON REPLACE(g_ref.ref_paperid::text, '"', '') = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON REPLACE(g_ref.paperid::text, '"', '') = ln.paperid

LEFT JOIN author_details ad
  ON REPLACE(g_ap.authorid::text, '"', '') = ad.authorid;