SELECT
    MIN(p3.paperid) AS min_ref_paperid,
    MIN(a.authorid) AS author,
    MIN(n.newsfeed_id) AS newsfeed
FROM Papers p1

JOIN PaperReferences r1
    ON p1.paperid = r1.citing_paperid
JOIN Papers p5
    ON r1.cited_paperid = p5.paperid
JOIN PaperReferences r2
    ON p5.paperid = r2.citing_paperid
JOIN Papers p6
    ON r2.cited_paperid = p6.paperid
JOIN PaperReferences r3
    ON p6.paperid = r3.citing_paperid
JOIN Papers p3
    ON r3.cited_paperid = p3.paperid

/* ===== author ===== */
LEFT JOIN Papers_to_Authors ap
    ON p1.paperid = ap.paperid
LEFT JOIN Authors_Gender a
    ON ap.authorid = a.authorid

/* ===== newsfeed ===== */
LEFT JOIN Link_Newsfeed ln
    ON p1.paperid = ln.paperid
LEFT JOIN Newsfeed_Metadata n
    ON ln.newsfeed_id = n.newsfeed_id

WHERE p1.paperid = 'W4235901390';