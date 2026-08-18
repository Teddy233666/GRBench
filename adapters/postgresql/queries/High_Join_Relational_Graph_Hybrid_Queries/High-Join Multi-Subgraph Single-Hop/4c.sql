SELECT
    MIN(g_ref.paperid::text) AS minPaper,
    MIN(g_ap.authorid::text) AS minAuthor,
    MIN(s.sourceid::text) AS minSource,
    MIN(ln.laureate_id::text) AS minNobel,
    MIN(ad.display_name::text) AS mindisplay_name
FROM
cypher('sciscinet_graph', $$
    MATCH (p:Papers) -[:PaperReferences]->(ref:Papers)
    WHERE p.paperid = 'W4211259235'
    AND toInteger(ref.citation_count) < 5
    RETURN p.paperid, ref.paperid
$$) AS g_ref(paperid agtype, ref_paperid agtype)

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (a:Authors_Gender)-[:Authors_Paper]->(p:Papers)
    WHERE a.h_index>80
    RETURN a.authorid, p.paperid
$$) AS g_ap(authorid agtype, paperid agtype)
ON g_ap.paperid::text = g_ref.paperid::text

LEFT JOIN papersources ps
  ON g_ref.ref_paperid::text = ps.paperid
LEFT JOIN sources s
  ON ps.sourceid = s.sourceid
LEFT JOIN link_nobellaureates ln
  ON g_ref.paperid::text = ln.paperid
LEFT JOIN author_details ad
  ON g_ap.authorid::text = ad.authorid;
