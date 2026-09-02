SELECT
    MIN(p1.paperid)         AS minPaper,
    MIN(ag.authorid)       AS minAuthor1,
    MIN(nsf.award_id)      AS award_id,
    MIN(s.sourceid)        AS minSource,
    MIN(lp.patent)    AS minNobel,
    MIN(ad.authorid)       AS minAuthorid2

FROM Papers p1

/* ===== 第1跳 ===== */
INNER JOIN PaperReferences r1
    ON p1.paperid = r1.citing_paperid
INNER JOIN Papers p2
    ON r1.cited_paperid = p2.paperid

/* ===== 第2跳 ===== */
INNER JOIN PaperReferences r2
    ON p2.paperid = r2.citing_paperid
INNER JOIN Papers p3
    ON r2.cited_paperid = p3.paperid

/* ===== 第3跳 ===== */
INNER JOIN PaperReferences r3
    ON p3.paperid = r3.citing_paperid
INNER JOIN Papers p4
    ON r3.cited_paperid = p4.paperid
   AND p4.citation_count < 80


/* ===== Authors (对应 GRAPH_TABLE ap) ===== */
LEFT JOIN Authors_Paper ap
    ON p4.paperid = ap.paperid

LEFT JOIN Authors_Gender ag
    ON ap.authorid = ag.authorid
   AND ag.h_index > 30


/* ===== NSF (对应 GRAPH_TABLE nsf) ===== */
LEFT JOIN Link_NSF lnsf
    ON p1.paperid = lnsf.paperid

LEFT JOIN NSF_Metadata nsf
    ON lnsf.award_id = nsf.award_id


/* ===== Source ===== */
LEFT JOIN papersources ps
    ON p4.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


LEFT JOIN link_patents lp
  ON p1.paperid = lp.paperid

/* ===== author_details ===== */
LEFT JOIN author_details ad
    ON ag.authorid = ad.authorid


WHERE
    p1.paperid = 'W2122344208';