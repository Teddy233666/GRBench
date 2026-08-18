DELETE FROM sciscinet_graph."Papers_to_Authors" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."Papers_to_Authors" e
  JOIN grbench_update6_papers_to_authors b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."affiliated_with" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."affiliated_with" e
  JOIN grbench_update6_affiliated_with b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."Authors_Gender" a
WHERE ctid IN (
  SELECT a.ctid
  FROM sciscinet_graph."Authors_Gender" a
  JOIN grbench_update6_authors_gender b ON a.id = b.id
);
