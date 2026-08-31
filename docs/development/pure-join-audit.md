# Pure Join Restoration Audit

Pure Join contains 96 alternate relational implementations of the 96 logical
main queries. They are distinct performance inputs even though each maps to the
same logical query ID. `benchmark/manifests/pure_join_variants.csv` records that
mapping.

## Published Coverage

| Adapter | Published | Status |
| --- | ---: | --- |
| AgensGraph | 96 | Static signatures match the authoritative SQL |
| ArangoDB | 96 | 72 audited; 24 requested legacy files are unverified |
| DuckDB | 96 | Byte-identical canonical mirror |
| GrainDB | 96 | Static signatures match the authoritative SQL |
| Kuzu | 0 | All 96 historical files are byte-identical to main Cypher |
| OrientDB | 96 | Static signatures match after eight corrections |
| PostgreSQL | 96 | Static signatures match the authoritative SQL |

The unverified ArangoDB groups are `2a-c`, `11a-c`, `13a-c`, `16a-c`,
`17a-c`, `23a-c`, `31a-c`, and `32a-c`. Their requested authoritative legacy
files are present for inspection and execution experiments, but adapter
coverage marks them `legacy_unverified` rather than audited implementations.

OrientDB corrections remove stale affiliation predicates in `13a-c`, restore
the anchor and patent endpoint in `17a-c`, and restore the `26c` and `29c`
thresholds.

Static review checks anchors, numeric predicates, logical edge dependencies,
inventory, and selected high-risk endpoints. It does not prove full result
equivalence or runtime support. Every published variant still requires a live
healthy-database smoke test and an independent result oracle before its output
is marked comparable.
