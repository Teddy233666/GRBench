SELECT
   MIN(p.paperid)      AS minPaper,
    MIN(a.authorid)       AS minAuthor,
    MIN(cf.paperid)       AS minAff,
    MIN(s.sourceid)       AS minSource,
    MIN(ln.laureate_id)   AS minNobel,
    MIN(ad.authorid)      AS minPatent
FROM
    Papers p

    -- 第1跳
    INNER JOIN PaperReferences r1
        ON p.paperid = r1.citing_paperid
    INNER JOIN Papers p1
        ON r1.cited_paperid = p1.paperid

    -- 第2跳
    INNER JOIN PaperReferences r2
        ON p1.paperid = r2.citing_paperid
    INNER JOIN Papers p2
        ON r2.cited_paperid = p2.paperid

    -- 第3跳
    INNER JOIN PaperReferences r3
        ON p2.paperid = r3.citing_paperid
    INNER JOIN Papers ref
        ON r3.cited_paperid = ref.paperid
       AND ref.citation_count < 5

    -- 作者 (对应 g_ap)
    LEFT JOIN Authors_Paper ap
        ON p.paperid = ap.paperid
    LEFT JOIN Authors_Gender a
        ON ap.authorid = a.authorid
       AND a.h_index > 80

    -- 机构 (对应 g_cf)
    LEFT JOIN contributed_from cf
        ON ref.paperid = cf.paperid
    LEFT JOIN Affiliations inst
        ON cf.institution_id = inst.institutionid
       AND inst.productivity > 10000

    -- 期刊来源
    LEFT JOIN papersources ps
        ON ref.paperid = ps.paperid
    LEFT JOIN sources s
        ON ps.sourceid = s.sourceid

    -- 诺奖
    LEFT JOIN link_nobellaureates ln
        ON p.paperid = ln.paperid

    -- 专利
    LEFT JOIN author_details ad
        ON a.authorid = ad.authorid

WHERE
    p.paperid = 'W2122344208';