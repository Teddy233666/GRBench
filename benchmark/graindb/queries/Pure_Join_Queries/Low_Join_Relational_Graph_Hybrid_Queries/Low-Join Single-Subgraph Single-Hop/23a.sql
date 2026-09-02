SELECT
    MIN(p.paperid) AS cited_paperid,
    MIN(lp.patent) AS minNobel
FROM Papers p

/* ===== NSF（必须存在） ===== */
INNER JOIN Link_NSF lnsf
    ON p.paperid = lnsf.paperid

INNER JOIN NSF_Metadata nsf
    ON lnsf.award_id = nsf.award_id

/* ===== 诺奖信息（可选） ===== */
LEFT JOIN link_patents lp
  ON p.paperid = lp.paperid
/* ===== 过滤条件 ===== */
WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 3;