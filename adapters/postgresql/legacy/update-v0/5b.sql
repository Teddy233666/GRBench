DELETE FROM sciscinet_graph."Papers_to_Authors" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."Papers_to_Authors" e
  JOIN grbench_update5_papers_to_authors b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);
