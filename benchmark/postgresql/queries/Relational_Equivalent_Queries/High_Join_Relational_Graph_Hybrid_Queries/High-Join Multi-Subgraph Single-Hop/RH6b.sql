SELECT
    MIN(ref.paperid)     AS p3,
    MIN(nm.newsfeed_id)  AS newsfeed,
    MIN(s.sourceid)      AS minSource,
    MIN(ln.laureate_id)  AS minNobel,
    MIN(lp.patent)       AS minPatent

FROM Papers p


/* ===== 一跳引用 ===== */
INNER JOIN PaperReferences r1
    ON p.paperid = r1.citing_paperid

INNER JOIN Papers ref
    ON r1.cited_paperid = ref.paperid
   AND ref.citation_count < 80


/* ===== Newsfeed ===== */
LEFT JOIN link_newsfeed lnf
    ON p.paperid = lnf.paperid

LEFT JOIN Newsfeed_Metadata nm
    ON lnf.newsfeed_id = nm.newsfeed_id


/* ===== Source ===== */
LEFT JOIN papersources ps
    ON p.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid


/* ===== Patent ===== */
LEFT JOIN link_patents lp
    ON p.paperid = lp.paperid


WHERE
    p.paperid = 'W4211259235';