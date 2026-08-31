SELECT
    MIN(p1.paperid)      AS cited_paperid,
    MIN(s.sourceid)      AS minSource,
    MIN(ln.laureate_id)  AS minNobel,
    MIN(lp.patent)       AS minPatent

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
   AND p4.citation_count < 5


/* ===== Source (连接 cited paper) ===== */
LEFT JOIN papersources ps
    ON p4.paperid = ps.paperid
LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel (连接 orig paper) ===== */
LEFT JOIN link_nobellaureates ln
    ON p1.paperid = ln.paperid


/* ===== Patent (连接 orig paper) ===== */
LEFT JOIN link_patents lp
    ON p1.paperid = lp.paperid


WHERE
    p1.paperid = 'W2122344208';