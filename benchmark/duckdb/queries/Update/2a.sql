DELETE FROM PaperReferences r
WHERE EXISTS (
        SELECT 1
        FROM grbench_update2_edges e
        WHERE
            e.citing_paperid = r.citing_paperid
            AND e.cited_paperid = r.cited_paperid
    );
