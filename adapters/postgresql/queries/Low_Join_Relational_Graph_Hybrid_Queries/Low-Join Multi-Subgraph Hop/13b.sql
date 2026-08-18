
SELECT
    MIN(g_ref.paperid::text) AS minPaper,
    MIN(g_ap.authorid::text) AS minAuthor,
    MIN(g_cf.paperid::text) AS minAff,
    MIN(ln.laureate_id::text) AS minNobel,
    MIN(ad.display_name::text) AS mindisplay_name
FROM
cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:PaperReferences]->(p1:Papers)
          -[:PaperReferences]->(p2:Papers)
          -[:PaperReferences]->(ref:Papers)
    WHERE p.paperid = 'W2122344208'
    AND toInteger(ref.citation_count) < 80
    RETURN p.paperid, ref.paperid
$$) AS g_ref(paperid agtype, ref_paperid agtype)

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (a:Authors_Gender)-[:Authors_Paper]->(p:Papers)
    WHERE toInteger(a.h_index)>30
    RETURN a.authorid, p.paperid
$$) AS g_ap(authorid agtype, paperid agtype)
ON g_ap.paperid::text = g_ref.paperid::text

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:contributed_from]->(inst:Affiliations)
    WHERE toInteger(inst.productivity)>5000
    RETURN p.paperid
$$) AS g_cf(paperid agtype)
ON g_ref.ref_paperid::text = g_cf.paperid::text
LEFT JOIN link_nobellaureates ln
  ON g_ref.paperid::text = ln.paperid
LEFT JOIN author_details ad
  ON g_ap.authorid::text = ad.authorid;
