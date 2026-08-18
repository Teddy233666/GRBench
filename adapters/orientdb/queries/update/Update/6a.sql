DELETE EDGE Papers_to_Authors
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);

DELETE EDGE affiliated_with
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender);

DELETE FROM Authors_Gender
WHERE authorid IN (SELECT authorid FROM grbench_update4_authors_gender) UNSAFE;
