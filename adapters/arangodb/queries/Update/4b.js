db._query(`
FOR a IN grbench_update4_authors_gender
  INSERT MERGE(UNSET(a, '_id', '_key', '_rev'), { _key: a.authorid }) INTO Authors_Gender
`);
