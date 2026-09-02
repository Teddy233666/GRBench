SELECT
    MIN(REPLACE((ref.paper_id)::text, '"', '')) AS minPaper,
    MIN(REPLACE((nsf.award_id)::text, '"', '')) AS award_id,
    MIN(s.sourceid) AS minSource,
    MIN(ln.laureate_id) AS minNobel,
    MIN(lp.patent) AS minPatent
FROM
(
    MATCH (p4:Papers)-[r1:PaperReferences]->(ref:Papers)
    WHERE p4.paperid='W4211259235'
    AND ref.citation_count<5
    RETURN
        p4.paperid  AS paper_id,
        ref.paperid AS ref_paper_id
) ref

LEFT JOIN
(
    MATCH (p2:Papers)-[ln:Link_NSF]->(n:NSF_Metadata)

    RETURN
        p2.paperid        AS paper_id,
        n.award_id        AS award_id,
        n.type_crossref   AS funder_name
) nsf
ON REPLACE((ref.paper_id)::text, '"', '') = REPLACE((nsf.paper_id)::text, '"', '')


LEFT JOIN papersources ps
  ON REPLACE((ref.ref_paper_id)::text, '"', '') = ps.paperid
LEFT JOIN sources s
  ON ps.sourceid = s.sourceid
LEFT JOIN link_nobellaureates ln
  ON REPLACE((ref.paper_id)::text, '"', '') = ln.paperid
LEFT JOIN link_patents lp
  ON REPLACE((ref.ref_paper_id)::text, '"', '') = lp.paperid;