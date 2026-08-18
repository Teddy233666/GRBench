# System Adapters

| Adapter | Main | Shortest Path | Update | Published implementation |
| --- | ---: | ---: | ---: | --- |
| AgensGraph | 96 | 0 | 0 | static SQL |
| ArangoDB | 96 | 15 | 0 | static JavaScript/AQL |
| DuckDB | 96 | 15 | 12 | canonical SQL directly |
| GrainDB | 96 | 0 | 12 | static SQL |
| Kuzu | 96 | 15 | 12 | Cypher plus runtime generation |
| OrientDB | 96 | 15 | 12 | native graph SQL and runner |
| PostgreSQL | 96 | 0 | 0 | static SQL |

These numbers describe published query coverage, not successful or comparable
benchmark rows. `benchmark/manifests/adapter_coverage.csv` is authoritative.

Kuzu and OrientDB have repository-relative Python entry points and dedicated
documentation. The other systems currently retain audited query translations
and historical loaders/runners; their `legacy-runner/` scripts contain old
host assumptions and are not formal entry points. New portable runners must
implement `docs/benchmark-contract.md` before replacing that status.

All adapters must load `canonical_full_v1`, record engine versions, and keep
credentials outside command history and source files.
