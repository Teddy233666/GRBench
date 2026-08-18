SELECT
    MIN(t.paperid) AS minPaper,
    MIN(t1.authorid) AS minAuthor,
    MIN(cf.institutionid) AS minAff,
    MIN(ln.laureate_id) AS minNobel,
    MIN(ad.authorid) AS minPatent
FROM
(
  SELECT DISTINCT
      p.paperid,
      ref.paperid AS ref_paperid,
      ref.citation_count
  FROM (p:Papers)-[r1:PaperReferences*3..3]->(ref:Papers)
  WHERE p.paperid = 'W2122344208'
    AND ref.citation_count < 5
) t

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      a.authorid
  FROM (p:Papers)-[pa:Papers_to_Authors]->(a:Authors_Gender)
  WHERE a.h_index > 80
) t1
ON t.paperid = t1.paperid

LEFT JOIN
(
  SELECT DISTINCT
      p.paperid,
      inst.institutionid
  FROM (p:Papers)-[cf:contributed_from]->(inst:Affiliations)
  WHERE inst.productivity > 10000
) cf
ON t.ref_paperid = cf.paperid

LEFT JOIN link_nobellaureates ln
  ON t.paperid = ln.paperid

LEFT JOIN author_details ad
  ON t1.authorid = ad.authorid;