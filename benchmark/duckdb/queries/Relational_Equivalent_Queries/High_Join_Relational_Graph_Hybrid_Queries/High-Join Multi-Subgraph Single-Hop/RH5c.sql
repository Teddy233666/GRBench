SELECT
    MIN(p.paperid)       AS minPaper,
    MIN(nsf.award_id)      AS award_id,
    MIN(s.sourceid)        AS minSource,
    MIN(ln.laureate_id)    AS minNobel,
    MIN(lp.patent)         AS minPatent

FROM Papers p

/* ===== 一跳引用 ===== */
INNER JOIN PaperReferences r1
    ON p.paperid = r1.citing_paperid

INNER JOIN Papers ref
    ON r1.cited_paperid = ref.paperid
   AND ref.citation_count < 5


/* ===== NSF 资助 ===== */
LEFT JOIN Link_NSF lnsf
    ON p.paperid = lnsf.paperid

LEFT JOIN NSF_Metadata nsf
    ON lnsf.award_id = nsf.award_id


/* ===== Source (连接 ref) ===== */
LEFT JOIN papersources ps
    ON ref.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid


/* ===== Patent (连接 ref) ===== */
LEFT JOIN link_patents lp
    ON ref.paperid = lp.paperid


WHERE
    p.paperid = 'W4211259235';