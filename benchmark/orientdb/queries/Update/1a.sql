DELETE EDGE PaperReferences
WHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers)
   OR cited_paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Papers_to_Authors
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Authors_Paper
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE contributed_from
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE PaperFields
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Link_NSF
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Link_NIH
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE Link_ClinicalTrials
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE link_newsfeed
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE EDGE link_twitter
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DELETE FROM Papers
WHERE year BETWEEN 2020 AND 2025 UNSAFE;
