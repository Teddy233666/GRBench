db._query(`
FOR p IN Papers
  FILTER p.year >= 2020 AND p.year <= 2025
  REMOVE p IN Papers
`);
