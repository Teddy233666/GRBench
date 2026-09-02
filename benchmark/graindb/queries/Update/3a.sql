DELETE FROM PaperReferences
WHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers)
   OR cited_paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Papers_to_Authors
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM contributed_from
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM PaperFields
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Link_NSF
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Link_NIH
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Link_ClinicalTrials
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM link_newsfeed
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM link_twitter
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Papers
WHERE year BETWEEN 2020 AND 2025;
