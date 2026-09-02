db._query(`
FOR p IN grbench_update1_papers
  INSERT MERGE(UNSET(p, '_id', '_key', '_rev'), { _key: p.paperid }) INTO Papers
`);