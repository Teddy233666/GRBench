DELETE FROM sciscinet_graph."PaperReferences" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."PaperReferences" e
  JOIN grbench_update2_edges b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);
