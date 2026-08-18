DELETE FROM sciscinet_graph."Authors_Gender" a
WHERE ctid IN (
  SELECT a.ctid
  FROM sciscinet_graph."Authors_Gender" a
  JOIN grbench_update6_authors_gender b ON a.id = b.id
);
