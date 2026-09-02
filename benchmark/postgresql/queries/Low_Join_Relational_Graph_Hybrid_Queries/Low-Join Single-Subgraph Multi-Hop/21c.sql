SELECT
    MIN(pr.paperid::text)            AS cited_paperid,
    MIN(h0.fieldid::text) AS fieldid0,
    MIN(lp.patent::text) AS minPatent
FROM

cypher('sciscinet_graph', $$
    MATCH (orig:Papers)-[:PaperReferences]->(p2:Papers)
          -[:PaperReferences]->(p3:Papers)
          -[:PaperReferences]->(cited:Papers)
    WHERE orig.paperid = 'W2122344208'
     AND toInteger(cited.citation_count) < 5
    RETURN orig.paperid,cited.paperid
$$) AS pr(paperid agtype,cited_paperid agtype)


LEFT JOIN hit_papers_level0 h0
  ON pr.paperid::text = h0.paperid
LEFT JOIN link_patents lp
  ON pr.cited_paperid::text = lp.paperid;