SELECT
    MIN(p.paperid) AS cited_paperid,
    MIN(ln.laureate_id) AS minNobel
FROM Papers p

/* ===== NIH 资助（必须存在） ===== */
INNER JOIN Link_NIH lnih
    ON p.paperid = lnih.paperid

INNER JOIN NIH_Metadata nih
    ON lnih.award_id = nih.award_id

/* ===== 诺奖信息 ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid

/* ===== 过滤条件 ===== */
WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 1;