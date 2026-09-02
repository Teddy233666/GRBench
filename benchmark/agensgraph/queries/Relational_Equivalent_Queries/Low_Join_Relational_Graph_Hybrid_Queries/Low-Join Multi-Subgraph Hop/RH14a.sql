SELECT
   MIN(p4.paperid)        AS minPaper,
    MIN(ag.authorid)       AS minAuthor1,
    MIN(nsf.award_id)       AS award_id,
    MIN(ln.laureate_id)     AS minNobel,
    MIN(ad.authorid)        AS minAuthorid2

FROM Papers p4


/* ===== 3-hop citation path ===== */
INNER JOIN PaperReferences r1
    ON p4.paperid = r1.citing_paperid
INNER JOIN Papers p5
    ON r1.cited_paperid = p5.paperid

INNER JOIN PaperReferences r2
    ON p5.paperid = r2.citing_paperid
INNER JOIN Papers p6
    ON r2.cited_paperid = p6.paperid

INNER JOIN PaperReferences r3
    ON p6.paperid = r3.citing_paperid
INNER JOIN Papers ref
    ON r3.cited_paperid = ref.paperid
   AND ref.citation_count < 150


/* ===== Authors (correct anchor = ref) ===== */
LEFT JOIN Authors_Paper ap
    ON ref.paperid = ap.paperid

LEFT JOIN Authors_Gender ag
    ON ap.authorid = ag.authorid
   AND ag.h_index > 10


/* ===== NSF (must match Graph_TABLE branch semantics) ===== */
LEFT JOIN Link_NSF lnsf
    ON p4.paperid = lnsf.paperid

LEFT JOIN NSF_Metadata nsf
    ON lnsf.award_id = nsf.award_id


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p4.paperid = ln.paperid


/* ===== author_details ===== */
LEFT JOIN author_details ad
    ON ag.authorid = ad.authorid


WHERE
    p4.paperid = 'W2122344208';