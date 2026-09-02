SELECT
    $q0[0].v AS min_ref_paper_id,
    $q1[0].v AS award_id
LET
    $q0 = (SELECT MIN(ref_paper_id) AS v
FROM (
    MATCH {class:Papers, as:p4, where:(paperid LIKE 'W423590139%' AND citation_count <= 3)}.out('PaperReferences'){class:Papers, as:ref} RETURN ref.paperid AS ref_paper_id
)),
    $q1 = (SELECT MIN(award_id) AS v
FROM (
    MATCH {class:Papers, as:p4, where:(paperid LIKE 'W423590139%' AND citation_count <= 3)}.out('PaperReferences'){class:Papers, as:ref}, {as:p4}.out('Link_NSF'){class:NSF_Metadata, as:nsf} RETURN nsf.award_id AS award_id
));
