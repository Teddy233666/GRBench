SELECT
    MIN(p.paperid)       AS cited_paperid,
    MIN(s.sourceid)      AS minSource,
    MIN(ln.laureate_id)  AS minNobel,
    MIN(lp.patent)       AS minPatent

FROM Papers p


/* ===== NIH edge constraint ===== */
INNER JOIN Link_NIH lnih
    ON p.paperid = lnih.paperid

INNER JOIN NIH_Metadata nm
    ON lnih.award_id = nm.award_id


/* ===== Source ===== */
LEFT JOIN papersources ps
    ON p.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel / Patent ===== */
LEFT JOIN link_nobellaureates ln
    ON p.paperid = ln.paperid

LEFT JOIN link_patents lp
    ON p.paperid = lp.paperid


/* ===== filters ===== */
WHERE
    p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 1;