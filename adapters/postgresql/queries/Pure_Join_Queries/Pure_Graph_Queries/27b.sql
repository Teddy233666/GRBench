SELECT
    MIN(p.paperid) AS paperid
FROM Papers p

/* ===== NIH（必须存在） ===== */
JOIN Link_NIH ln
    ON p.paperid = ln.paperid

JOIN NIH_Metadata n_nih
    ON ln.paperid = n_nih.paperid   --（若你库是 award_id 版本可换）

/* ===== NSF（可选） ===== */
LEFT JOIN Link_NSF ls
    ON p.paperid = ls.paperid

LEFT JOIN NSF_Metadata n_nsf
    ON ls.award_id = n_nsf.award_id

/* ===== 过滤条件 ===== */
WHERE p.paperid LIKE 'W423590139%'
  AND p.citation_count <= 1;