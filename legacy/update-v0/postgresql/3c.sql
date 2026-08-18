DELETE FROM sciscinet_graph."PaperReferences" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."PaperReferences" e
  JOIN grbench_update3_paperreferences b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."Papers_to_Authors" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."Papers_to_Authors" e
  JOIN grbench_update3_papers_to_authors b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."contributed_from" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."contributed_from" e
  JOIN grbench_update3_contributed_from b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."PaperFields" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."PaperFields" e
  JOIN grbench_update3_paperfields b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."Link_NSF" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."Link_NSF" e
  JOIN grbench_update3_link_nsf b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."Link_NIH" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."Link_NIH" e
  JOIN grbench_update3_link_nih b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."Link_ClinicalTrials" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."Link_ClinicalTrials" e
  JOIN grbench_update3_link_clinicaltrials b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."link_newsfeed" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."link_newsfeed" e
  JOIN grbench_update3_link_newsfeed b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."link_twitter" e
WHERE ctid IN (
  SELECT e.ctid
  FROM sciscinet_graph."link_twitter" e
  JOIN grbench_update3_link_twitter b
    ON e.start_id = b.start_id
   AND e.end_id = b.end_id
);

DELETE FROM sciscinet_graph."Papers" p
WHERE ctid IN (
  SELECT p.ctid
  FROM sciscinet_graph."Papers" p
  JOIN grbench_update1_papers b ON p.id = b.id
);
