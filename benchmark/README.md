# Benchmark Implementations

Each system directory contains exactly three workflow phases:

- `loaders/`: schema, import, and index construction;
- `queries/`: native H, G, S, RH, RG, and U implementations; the six
  relational-capable systems also provide S-series equivalents under
  `Relational_Equivalent_Queries/Shortest_Path_Queries/`;
- `runners/`: execution and resource measurement.

Query IDs follow the paper and are documented in
[`../docs/query-naming.md`](../docs/query-naming.md). Implementations are kept
per system because syntax, graph direction, path support, Update isolation, and
result materialization differ. Do not infer semantic equivalence from matching
filenames alone; use result/state oracles.
