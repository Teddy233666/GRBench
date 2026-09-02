SELECT
    MIN(p.paperid)       AS cited_paperid,
    MIN(s.sourceid)      AS minSource,
    MIN(h1.paperid) AS minh1paperid,
    MIN(lp.patent)       AS minPatent

FROM Papers p


/* ===== ClinicalTrials edge constraint ===== */
INNER JOIN Link_ClinicalTrials lct
    ON p.paperid = lct.paperid

INNER JOIN clinicaltrials_metadata cm
    ON lct.nct_id = cm.nct_id


/* ===== Source ===== */
LEFT JOIN papersources ps
    ON p.paperid = ps.paperid

LEFT JOIN sources s
    ON ps.sourceid = s.sourceid


/* ===== Nobel / Patent ===== */
LEFT JOIN hit_papers_level1 h1
  ON p.paperid = h1.paperid
LEFT JOIN link_patents lp
    ON p.paperid = lp.paperid


/* ===== filters ===== */
WHERE
    p.paperid LIKE 'W423590139%'
    AND p.citation_count <= 1;
