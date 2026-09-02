
SELECT
    MIN(pr.paperid::text)            AS cited_paperid,
    MIN(src_table.sourceid::text) AS minSource
FROM

cypher('sciscinet_graph', $$
    MATCH (orig:Papers)-[:PaperReferences]->(p2:Papers)
          -[:PaperReferences]->(p3:Papers)
          -[:PaperReferences]->(cited:Papers)
    WHERE orig.paperid = 'W2122344208'
      AND toInteger(cited.citation_count) < 5
    RETURN orig.paperid,cited.paperid
$$) AS pr(paperid agtype,cited_paperid agtype)

LEFT JOIN papersources ps_table
  ON pr.paperid::text = ps_table.paperid

LEFT JOIN sources src_table
  ON ps_table.sourceid = src_table.sourceid;