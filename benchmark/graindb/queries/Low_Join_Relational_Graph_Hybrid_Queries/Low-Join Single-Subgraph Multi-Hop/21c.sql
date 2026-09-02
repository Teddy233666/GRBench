SELECT
    MIN(t.cited_paperid) AS cited_paperid,
    MIN(h0.fieldid) AS fieldid,
    MIN(lp.patent) AS minPatent
FROM
(
  SELECT DISTINCT
      orig.paperid AS orig_paperid,
      cited.paperid AS cited_paperid,
      cited.citation_count
  FROM (orig:Papers)-[r1:PaperReferences*3..3]->(cited:Papers)
  WHERE orig.paperid = 'W2122344208'
    AND cited.citation_count < 5
) t

LEFT JOIN hit_papers_level0 h0
  ON t.orig_paperid = h0.paperid

LEFT JOIN link_patents lp
  ON t.cited_paperid = lp.paperid;
