SELECT
    MIN(orig.paperid) AS cited_paperid,
    MIN(s.sourceid) AS minSource
FROM Papers orig

/* ===== 第1跳引用 ===== */
INNER JOIN PaperReferences r1
    ON orig.paperid = r1.citing_paperid
INNER JOIN Papers p2
    ON r1.cited_paperid = p2.paperid

/* ===== 第2跳引用 ===== */
INNER JOIN PaperReferences r2
    ON p2.paperid = r2.citing_paperid
INNER JOIN Papers p3
    ON r2.cited_paperid = p3.paperid

/* ===== 第3跳引用 ===== */
INNER JOIN PaperReferences r3
    ON p3.paperid = r3.citing_paperid
INNER JOIN Papers cited
    ON r3.cited_paperid = cited.paperid
    AND cited.citation_count < 80

/* ===== papersources + sources ===== */
LEFT JOIN papersources ps
    ON orig.paperid = ps.paperid   -- ✅ 修改2（唯一修改）

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid

/* ===== 起始论文条件 ===== */
WHERE orig.paperid = 'W2122344208';