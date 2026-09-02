SELECT
    MIN(p3.paperid)     AS p3,
    MIN(nf.newsfeed_id)    AS newsfeed,
    MIN(ln.laureate_id) AS minNobel

FROM Papers p1


/* ===== 1-hop citation ===== */
INNER JOIN PaperReferences r
    ON p1.paperid = r.citing_paperid
INNER JOIN Papers p3
    ON r.cited_paperid = p3.paperid
   AND p3.citation_count < 150


/* ===== Newsfeed (side branch) ===== */
LEFT JOIN link_newsfeed lnf
    ON p1.paperid = lnf.paperid

LEFT JOIN Newsfeed_Metadata nf
    ON lnf.newsfeed_id = nf.newsfeed_id


/* ===== Nobel (side branch) ===== */
LEFT JOIN link_nobellaureates ln
    ON p1.paperid = ln.paperid


WHERE
    p1.paperid = 'W2122344208';