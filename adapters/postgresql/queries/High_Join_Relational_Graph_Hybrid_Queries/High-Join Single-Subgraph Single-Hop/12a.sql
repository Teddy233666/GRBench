SELECT
    MIN(pn.paperid::text) AS cited_paperid,
    MIN(src_table.sourceid::text) AS minSource,
    MIN(h1.paperid::text) AS minh1paperid,
    MIN(lp.patent::text) AS minPatent
FROM cypher('sciscinet_graph', $$
    MATCH (p:Papers)-[:Link_ClinicalTrials]->(:clinicaltrials_metadata)
    WHERE p.paperid STARTS WITH 'W423590139'
      AND toInteger(p.citation_count) <= 3
    RETURN p.paperid
$$) AS pn(paperid agtype)
LEFT JOIN papersources ps_table ON pn.paperid::text = ps_table.paperid
LEFT JOIN sources src_table ON ps_table.sourceid = src_table.sourceid
LEFT JOIN hit_papers_level1 h1 ON pn.paperid::text = h1.paperid
LEFT JOIN link_patents lp ON pn.paperid::text = lp.paperid;
