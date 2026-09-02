SELECT MIN(paperid) AS ref_paperid
FROM Papers
WHERE citation_count < 80
  AND (
      paperid = 'W4211259235'
      OR paperid IN (SELECT cited_paperid FROM PaperReferences WHERE citing_paperid = 'W4211259235')
  );
