SELECT
    MIN(p.paperid)       AS cited_paperid,
    MIN(s.sourceid)      AS minSource,
    MIN(ln.laureate_id)  AS minNobel,
     MIN(h0.paperid)       AS minh0paperid

FROM Papers p


/* ===== NSF edge constraint ===== */
INNER JOIN Link_NSF lnsf
    ON p.paperid = lnsf.paperid

INNER JOIN NSF_Metadata nm
    ON lnsf.award_id = nm.award_id


/* ===== Source ===== */
LEFT JOIN papersources ps
    ON p.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel / Patent ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid

LEFT JOIN hit_papers_level0 h0
  ON p.paperid = h0.paperid


/* ===== filters ===== */
WHERE
    p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 1;