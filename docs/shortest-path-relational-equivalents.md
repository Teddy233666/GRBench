# Shortest-Path Relational Equivalents

Each relational-capable system has 15 files under
`benchmark/<system>/queries/Relational_Equivalent_Queries/Shortest_Path_Queries/`.
They retain the S-series IDs `S1a` through `S5c` and the original endpoint
predicates.

## Design

- SQL systems use recursive edge-table joins with a visited-set column. S1 and
  S4 use recursive closure, S2 and S3 cap expansion at three and four hops, and
  S5 expands the paper-reference edge for zero or one hop. S3 performs the
  `contributed_from` relation join after endpoint selection.
- ArangoDB uses edge-collection expansion with breadth-first/global-unique
  traversal and then collection-level joins. Its unbounded S1/S4 expressions
  use a large finite engine bound because AQL requires a finite traversal range.
- OrientDB uses SQL outer aggregation over `TRAVERSE` for its recursive closure;
  this is the engine's relationally composable fallback, not the native
  `shortestPath()` expression.
- Kuzu is intentionally excluded. Kuzu 0.11.3 accepts Cypher, not SQL, so a
  SQL relation expression would be neither executable nor a valid Kuzu adapter
  query. Its native S-series remains under `benchmark/kuzu/queries/Shortest_Path_Queries/`.

The generated SQL source is maintained by
`scripts/generate_shortest_relational_equivalents.py`. These expressions are
structural translations and still require result-oracle comparison before
claiming semantic equivalence on a live database.
