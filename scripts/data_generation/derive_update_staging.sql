-- Derive the immutable support tables used by the 12 authoritative Updates.
-- Run this once against a healthy baseline before measuring any Update. The
-- setup is not itself a benchmark query and must remain outside timed regions.

DROP TABLE IF EXISTS grbench_update1_papers;
CREATE TABLE grbench_update1_papers AS
SELECT * FROM Papers WHERE CAST(year AS INTEGER) BETWEEN 2020 AND 2025;

DROP TABLE IF EXISTS grbench_update1_papers_to_authors;
CREATE TABLE grbench_update1_papers_to_authors AS
SELECT * FROM Papers_to_Authors
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update2_edges;
CREATE TABLE grbench_update2_edges AS
SELECT * FROM PaperReferences
WHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_paperreferences;
CREATE TABLE grbench_update3_paperreferences AS
SELECT * FROM PaperReferences
WHERE citing_paperid IN (SELECT paperid FROM grbench_update1_papers)
   OR cited_paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_authors_paper;
CREATE TABLE grbench_update3_authors_paper AS
SELECT * FROM Authors_Paper
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_contributed_from;
CREATE TABLE grbench_update3_contributed_from AS
SELECT * FROM contributed_from
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_paperfields;
CREATE TABLE grbench_update3_paperfields AS
SELECT * FROM PaperFields
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_link_nsf;
CREATE TABLE grbench_update3_link_nsf AS
SELECT * FROM Link_NSF
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_link_nih;
CREATE TABLE grbench_update3_link_nih AS
SELECT * FROM Link_NIH
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_link_clinicaltrials;
CREATE TABLE grbench_update3_link_clinicaltrials AS
SELECT * FROM Link_ClinicalTrials
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_link_newsfeed;
CREATE TABLE grbench_update3_link_newsfeed AS
SELECT * FROM link_newsfeed
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update3_link_twitter;
CREATE TABLE grbench_update3_link_twitter AS
SELECT * FROM link_twitter
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update4_authors_gender;
CREATE TABLE grbench_update4_authors_gender AS
SELECT * FROM Authors_Gender WHERE h_index BETWEEN 10 AND 20;

DROP TABLE IF EXISTS grbench_update5_papers_to_authors;
CREATE TABLE grbench_update5_papers_to_authors AS
SELECT * FROM Papers_to_Authors
WHERE paperid IN (SELECT paperid FROM grbench_update1_papers);

DROP TABLE IF EXISTS grbench_update6_papers_to_authors;
CREATE TABLE grbench_update6_papers_to_authors AS
SELECT * FROM Papers_to_Authors
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);

DROP TABLE IF EXISTS grbench_update6_affiliated_with;
CREATE TABLE grbench_update6_affiliated_with AS
SELECT * FROM affiliated_with
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);
