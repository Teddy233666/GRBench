DELETE EDGE PaperReferences
WHERE citing_paperid IN (
    SELECT citing_paperid
    FROM grbench_update2_edges
);
