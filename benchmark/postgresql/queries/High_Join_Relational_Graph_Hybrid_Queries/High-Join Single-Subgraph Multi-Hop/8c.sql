SELECT
    MIN(pr.paperid::text)            AS cited_paperid,
    MIN(h0.fieldid::text) AS fieldid0,
    MIN(h1.fieldid::text) AS fieldid1,
    MIN(ln.laureate_id::text) AS minNobel,
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
LEFT JOIN hit_papers_level1 h1
  ON pr.paperid::text = h1.paperid
LEFT JOIN link_nobellaureates ln
  ON pr.cited_paperid::text = ln.paperid

LEFT JOIN link_patents lp
  ON pr.cited_paperid::text = lp.paperid;