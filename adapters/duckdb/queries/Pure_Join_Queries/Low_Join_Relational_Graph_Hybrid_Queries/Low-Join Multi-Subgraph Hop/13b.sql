SELECT
    MIN(p1.paperid)        AS minPaper,
    MIN(ag.authorid)       AS minAuthor,
    MIN(inst.institutionid) AS minAff,
    MIN(ln.laureate_id)    AS minNobel,
    MIN(ad.authorid)       AS minPatent

FROM Papers p1


/* ===== 3-hop citation path ===== */
INNER JOIN PaperReferences r1
    ON p1.paperid = r1.citing_paperid
INNER JOIN Papers p2
    ON r1.cited_paperid = p2.paperid

INNER JOIN PaperReferences r2
    ON p2.paperid = r2.citing_paperid
INNER JOIN Papers p3
    ON r2.cited_paperid = p3.paperid

INNER JOIN PaperReferences r3
    ON p3.paperid = r3.citing_paperid
INNER JOIN Papers ref
    ON r3.cited_paperid = ref.paperid
   AND ref.citation_count < 80


/* ===== Authors (Graph: a -> ap -> p) ===== */
LEFT JOIN Authors_Paper ap
    ON p1.paperid = ap.paperid

LEFT JOIN Authors_Gender ag
    ON ap.authorid = ag.authorid
   AND ag.h_index > 30


/* ===== Affiliation (Graph: p -> cf -> inst) ===== */
LEFT JOIN contributed_from cf
    ON ref.paperid = cf.paperid

LEFT JOIN Affiliations inst
    ON cf.institution_id = inst.institutionid


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p1.paperid = ln.paperid


/* ===== author_details ===== */
LEFT JOIN author_details ad
    ON ag.authorid = ad.authorid


WHERE
    p1.paperid = 'W2122344208';