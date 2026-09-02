SELECT
    MIN(orig.paperid) AS cited_paperid,
    MIN(h0.fieldid) AS fieldid,
    MIN(lp.patent) AS minPatent
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
    AND cited.citation_count < 5

/* ===== 修正点：补回 field mapping ===== */
LEFT JOIN hit_papers_level0 h0
    ON orig.paperid = h0.paperid

/* ===== 专利 ===== */
LEFT JOIN link_patents lp
    ON cited.paperid = lp.paperid

WHERE orig.paperid = 'W2122344208';