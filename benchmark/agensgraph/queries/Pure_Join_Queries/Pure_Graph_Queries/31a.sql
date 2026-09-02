SELECT
    MIN(p4.paperid)       AS p3,
    MIN(f.fieldid)        AS fieldid

FROM Papers p1


/* ===== 第1跳 ===== */
INNER JOIN PaperReferences r1
    ON p1.paperid = r1.citing_paperid
INNER JOIN Papers p2
    ON r1.cited_paperid = p2.paperid


/* ===== 第2跳 ===== */
INNER JOIN PaperReferences r2
    ON p2.paperid = r2.citing_paperid
INNER JOIN Papers p3
    ON r2.cited_paperid = p3.paperid


/* ===== 第3跳 ===== */
INNER JOIN PaperReferences r3
    ON p3.paperid = r3.citing_paperid
INNER JOIN Papers p4
    ON r3.cited_paperid = p4.paperid
   AND p4.citation_count < 150


/* ===== PaperFields ===== */
LEFT JOIN PaperFields pf
    ON p4.paperid = pf.paperid
LEFT JOIN Fields f
    ON pf.fieldid = f.fieldid


WHERE
    p1.paperid = 'W2122344208';