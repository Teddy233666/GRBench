SELECT
    MIN(p4.paperid)       AS p3,
    MIN(f.fieldid)        AS fieldid,
    MIN(nm.newsfeed_id)   AS newsfeed,
    MIN(s.sourceid)       AS minSource,
    MIN(ln.laureate_id)   AS minNobel,
    MIN(lp.patent)        AS minPatent

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


/* ===== Newsfeed ===== */
LEFT JOIN link_newsfeed lnf
    ON p4.paperid = lnf.paperid
LEFT JOIN Newsfeed_Metadata nm
    ON lnf.newsfeed_id = nm.newsfeed_id


/* ===== Source ===== */
LEFT JOIN papersources ps
    ON p1.paperid = ps.paperid
LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p1.paperid = ln.paperid


/* ===== Patent ===== */
LEFT JOIN link_patents lp
    ON p1.paperid = lp.paperid


WHERE
    p1.paperid = 'W2122344208';