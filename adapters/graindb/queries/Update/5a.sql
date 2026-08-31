DELETE FROM Papers_to_Authors r
WHERE EXISTS (
        SELECT 1
        FROM grbench_update5_papers_to_authors e
        WHERE
            e.paperid = r.paperid
            AND e.authorid = r.authorid
    );