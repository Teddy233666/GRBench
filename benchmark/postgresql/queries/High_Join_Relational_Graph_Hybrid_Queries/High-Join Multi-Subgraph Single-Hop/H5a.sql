
SELECT
    MIN(ref.paper_id::text) AS minPaper,
    MIN(nsf.award_id::text) AS award_id,
    MIN(s.sourceid::text) AS minSource,
    MIN(ln.laureate_id::text) AS minNobel,
    MIN(lp.patent::text) AS minAuthorid2
FROM
cypher('sciscinet_graph', $$
    MATCH (p4:Papers)-[:PaperReferences]->(p5:Papers)
          -[:PaperReferences]->(p6:Papers)
          -[:PaperReferences]->(ref:Papers)
    WHERE p4.paperid = 'W4211259235'
    AND toInteger(ref.citation_count) < 150
    RETURN p4.paperid, ref.paperid
$$) AS ref(paper_id agtype, ref_paper_id agtype)

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (p2:Papers)-[:Link_NSF]->(n:NSF_Metadata)
    RETURN
        p2.paperid,
        n.award_id,
        n.type_crossref
$$) AS nsf(
    paper_id agtype,
    award_id agtype,
    funder_name agtype
)
ON ref.paper_id::text = nsf.paper_id::text

LEFT JOIN papersources ps
    ON ref.ref_paper_id::text = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
    ON ref.paper_id::text = ln.paperid

LEFT JOIN link_patents lp
  ON ref.ref_paper_id::text = lp.paperid;