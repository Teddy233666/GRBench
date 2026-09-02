INSERT INTO Authors_Gender
SELECT * FROM grbench_update4_authors_gender;

INSERT INTO Papers_to_Authors
SELECT * FROM grbench_update6_papers_to_authors;

INSERT INTO affiliated_with
SELECT * FROM grbench_update6_affiliated_with;
