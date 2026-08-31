SELECT
    MIN(ref.paperid) AS min_ref_paper_id,
    MIN(nsf.award_id) AS award_id
FROM Papers p4

JOIN PaperReferences r1
    ON p4.paperid = r1.citing_paperid

JOIN Papers ref
    ON r1.cited_paperid = ref.paperid

/* ===== NSF（修正 anchor）===== */
LEFT JOIN Link_NSF ln
    ON ref.paperid = ln.paperid

LEFT JOIN NSF_Metadata nsf
    ON ln.award_id = nsf.award_id

WHERE p4.paperid LIKE 'W423590139%'
  AND p4.citation_count = 1;