
db._query(`
  FOR a IN Authors_Gender
    FILTER a.h_index >= 10 AND a.h_index <= 20
    FOR p, r IN INBOUND a Papers_to_Authors
      REMOVE r IN Papers_to_Authors
  `);