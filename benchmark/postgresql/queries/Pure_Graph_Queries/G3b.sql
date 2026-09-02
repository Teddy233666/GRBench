SELECT
    MIN(g_ref.paperid::text),
    MIN(g_ap.award_id::text)
FROM

cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_NIH]->(n:NIH_Metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND toInteger(p.citation_count)<= 1
    RETURN p.paperid
$$) AS g_ref(paperid agtype)

LEFT JOIN

cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_NSF]->(n:NSF_Metadata)
    RETURN p.paperid,n.award_id
$$) AS g_ap(paperid agtype,award_id agtype)

ON g_ap.paperid::text = g_ref.paperid::text;