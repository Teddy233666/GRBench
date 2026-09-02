SELECT
    MIN(p1.paperid)      AS paperid,
    MIN(hp.fieldid)      AS fieldid0,
    MIN(h1.fieldid)      AS fieldid1,
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
   AND p4.citation_count < 150


/* ===== normalized citations ===== */
LEFT JOIN normalized_citations_level0 hp
    ON p1.paperid = hp.paperid

LEFT JOIN normalized_citations_level1 h1
    ON p1.paperid = h1.paperid


/* ===== Nobel / Patent ===== */
LEFT JOIN link_nobellaureates ln
    ON p4.paperid = ln.paperid

LEFT JOIN link_patents lp
    ON p4.paperid = lp.paperid


WHERE
    p1.paperid = 'W2122344208';