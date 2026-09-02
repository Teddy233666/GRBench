SELECT
    MIN(p3.paperid)        AS p3,
    MIN(f.fieldid)         AS fieldid,
    MIN(nf.newsfeed_id)    AS newsfeed,
    MIN(ln.laureate_id)    AS minNobel

FROM Papers p1


/* ===== 3-hop citation path ===== */
INNER JOIN PaperReferences r1
    ON p1.paperid = r1.citing_paperid
INNER JOIN Papers p5
    ON r1.cited_paperid = p5.paperid

INNER JOIN PaperReferences r2
    ON p5.paperid = r2.citing_paperid
INNER JOIN Papers p6
    ON r2.cited_paperid = p6.paperid

INNER JOIN PaperReferences r3
    ON p6.paperid = r3.citing_paperid
INNER JOIN Papers p3
    ON r3.cited_paperid = p3.paperid
   AND p3.citation_count < 150


/* ===== PaperFields (IMPORTANT: attach to p2 = p5 in path) ===== */
LEFT JOIN PaperFields pf
    ON p3.paperid = pf.paperid

LEFT JOIN Fields f
    ON pf.fieldid = f.fieldid


/* ===== Newsfeed (anchor = p1) ===== */
LEFT JOIN link_newsfeed lnf
    ON p1.paperid = lnf.paperid

LEFT JOIN Newsfeed_Metadata nf
    ON lnf.newsfeed_id = nf.newsfeed_id


/* ===== Nobel (anchor = p1) ===== */
LEFT JOIN link_nobellaureates ln
    ON p1.paperid = ln.paperid


WHERE
    p1.paperid = 'W2122344208';