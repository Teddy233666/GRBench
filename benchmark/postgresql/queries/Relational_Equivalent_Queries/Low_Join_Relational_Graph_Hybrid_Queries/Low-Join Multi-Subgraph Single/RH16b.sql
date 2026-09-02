SELECT
    MIN(p.paperid)         AS minPaper,
    MIN(ag.authorid)       AS minAuthor,
    MIN(ln.laureate_id)    AS minNobel,
    MIN(ad.authorid)       AS minPatent

FROM Papers p


/* ===== 1-hop citation ===== */
INNER JOIN PaperReferences r
    ON p.paperid = r.citing_paperid
INNER JOIN Papers ref
    ON r.cited_paperid = ref.paperid
   AND ref.citation_count < 80


/* ===== Authors (IMPORTANT: attach to ref) ===== */
LEFT JOIN Papers_to_Authors ap
    ON ref.paperid = ap.paperid

LEFT JOIN Authors_Gender ag
    ON ap.authorid = ag.authorid
   AND ag.h_index > 30


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid


/* ===== author_details ===== */
LEFT JOIN author_details ad
    ON ag.authorid = ad.authorid


WHERE
    p.paperid = 'W4211259235';