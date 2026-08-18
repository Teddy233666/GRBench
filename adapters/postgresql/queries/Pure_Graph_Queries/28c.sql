SELECT
    MIN(ref.ref_paper_id::text),
    MIN(nsf.award_id::text)
FROM

cypher('sciscinet_graph', $$
    MATCH (p4:Papers)-[:PaperReferences]->(ref:Papers)
    WHERE p4.paperid STARTS WITH 'W423590139'
      AND toInteger(p4.citation_count) =1
    RETURN p4.paperid, ref.paperid
$$) AS ref(paper_id agtype, ref_paper_id agtype)

LEFT JOIN

cypher('sciscinet_graph', $$
    MATCH (p2:Papers)-[:Link_NSF]->(n:NSF_Metadata)
    RETURN p2.paperid, n.award_id, n.type_crossref
$$) AS nsf(paper_id agtype, award_id agtype, funder_name agtype)

ON ref.paper_id::text = nsf.paper_id::text;