SELECT
    MIN(p.paperid) AS cited_paperid,
    MIN(ln.laureate_id) AS minNobel
FROM Papers p

/* ===== ClinicalTrials（必须存在） ===== */
INNER JOIN Link_ClinicalTrials lct
    ON p.paperid = lct.paperid

INNER JOIN clinicaltrials_metadata ct
    ON lct.nct_id = ct.nct_id

/* ===== 诺奖信息（可选） ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid

/* ===== 起始过滤条件 ===== */
WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 1;