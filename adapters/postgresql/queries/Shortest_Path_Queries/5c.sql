SELECT MIN(ref_paperid::text) AS ref_paperid
FROM cypher('sciscinet_graph', $$

    MATCH p = (a:Papers)-[r1:PaperReferences*0..1]->(ref:Papers)
    WHERE a.paperid = 'W4211259235'
      AND toFloat(ref.citation_count) < 80

    WITH p, a AS a_dummy, ref AS ref_dummy, length(p) AS hops

    WITH * ORDER BY hops ASC LIMIT 1

    RETURN a_dummy.paperid AS paperid,
           ref_dummy.paperid AS ref_paperid,
           ref_dummy.citation_count AS citation_count

$$) AS t(paperid agtype, ref_paperid agtype, citation_count agtype);