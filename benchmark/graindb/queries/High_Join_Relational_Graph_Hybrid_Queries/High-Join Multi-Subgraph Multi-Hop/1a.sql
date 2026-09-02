SELECT
    MIN(t.paperid1) AS minPaper,
    MIN(t1.authorid) AS minAuthor,
    MIN(t2.institutionid) AS minAff,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
  SELECT DISTINCT
      p.paperid AS paperid1,
      ref.paperid AS paperid2
  FROM (p:Papers)-[r1:PaperReferences*3..3]->(ref:Papers)
  WHERE p.paperid = 'W2122344208'
    AND ref.citation_count < 150
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      a.authorid
  FROM (p:Papers)-[pa:Papers_to_Authors]->(a:Authors_Gender)
  WHERE  a.h_index > 10
) t1
ON t.paperid1 = t1.paperid

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      inst.institutionid
  FROM (p:Papers)-[cf:contributed_from]->(inst:Affiliations)
  WHERE inst.productivity > 1000
) t2
ON t.paperid2 = t2.paperid

LEFT JOIN papersources ps
  ON t.paperid2 = ps.paperid

LEFT JOIN sources s
  ON ps.sourceid = s.sourceid

LEFT JOIN link_nobellaureates ln
  ON t.paperid1 = ln.paperid

LEFT JOIN author_details ad
  ON t1.authorid = ad.authorid;