INSERT INTO Papers
SELECT * FROM grbench_update1_papers;

INSERT INTO PaperReferences
SELECT * FROM grbench_update3_paperreferences;

INSERT INTO Papers_to_Authors
SELECT * FROM grbench_update1_papers_to_authors;

INSERT INTO Authors_Paper
SELECT * FROM grbench_update3_authors_paper;

INSERT INTO contributed_from
SELECT * FROM grbench_update3_contributed_from;

INSERT INTO PaperFields
SELECT * FROM grbench_update3_paperfields;

INSERT INTO Link_NSF
SELECT * FROM grbench_update3_link_nsf;

INSERT INTO Link_NIH
SELECT * FROM grbench_update3_link_nih;

INSERT INTO Link_ClinicalTrials
SELECT * FROM grbench_update3_link_clinicaltrials;

INSERT INTO link_newsfeed
SELECT * FROM grbench_update3_link_newsfeed;

INSERT INTO link_twitter
SELECT * FROM grbench_update3_link_twitter;
