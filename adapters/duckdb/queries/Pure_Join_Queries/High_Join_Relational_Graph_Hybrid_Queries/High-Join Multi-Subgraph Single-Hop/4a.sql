SELECT
    MIN(p.paperid)        AS minPaper,
    MIN(ag.authorid)      AS minAuthor,
    MIN(s.sourceid)       AS minSource,
    MIN(ln.laureate_id)   AS minNobel,
    MIN(ad.authorid)      AS minPatent

FROM Papers p

/* ===== 一跳引用 ===== */
INNER JOIN PaperReferences r1
    ON p.paperid = r1.citing_paperid

INNER JOIN Papers ref
    ON r1.cited_paperid = ref.paperid
   AND ref.citation_count < 150


/* ===== 作者 ===== */
LEFT JOIN Authors_Paper ap
    ON p.paperid = ap.paperid

LEFT JOIN Authors_Gender ag
    ON ap.authorid = ag.authorid
   AND ag.h_index > 10


/* ===== Source (连接 ref) ===== */
LEFT JOIN papersources ps
    ON ref.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid


/* ===== Author details ===== */
LEFT JOIN author_details ad
    ON ag.authorid = ad.authorid


WHERE
    p.paperid = 'W4211259235';