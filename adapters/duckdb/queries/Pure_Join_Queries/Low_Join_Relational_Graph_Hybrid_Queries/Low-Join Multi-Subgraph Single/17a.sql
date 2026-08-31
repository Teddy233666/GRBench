SELECT
    MIN(p4.paperid)     AS minPaper,
    MIN(nsf.award_id)     AS award_id,
    MIN(ln.laureate_id)   AS minNobel,
    MIN(lp.patent)        AS minPatent

FROM Papers p4


/* ===== 1-hop citation ===== */
INNER JOIN PaperReferences r
    ON p4.paperid = r.citing_paperid
INNER JOIN Papers ref
    ON r.cited_paperid = ref.paperid
   AND ref.citation_count < 150


/* ===== NSF ===== */
LEFT JOIN Link_NSF lnsf
    ON p4.paperid = lnsf.paperid

LEFT JOIN NSF_Metadata nsf
    ON lnsf.award_id = nsf.award_id


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p4.paperid = ln.paperid


/* ===== Patent (IMPORTANT FIX) ===== */
LEFT JOIN link_patents lp
    ON p4.paperid = lp.paperid


WHERE
    p4.paperid = 'W2122344208';