# System Adapters

| Adapter | Main | Shortest Path | Update | Guide |
| --- | ---: | ---: | ---: | --- |
| AgensGraph | 96 | 0 | 0 | [agensgraph.md](agensgraph.md) |
| ArangoDB | 96 | 15 | 0 | [arangodb.md](arangodb.md) |
| DuckDB | 96 | 15 | 12 | [duckdb.md](duckdb.md) |
| GrainDB | 96 | 0 | 12 | [graindb.md](graindb.md) |
| Kuzu | 96 | 15 | 12 | [kuzu.md](kuzu.md) |
| OrientDB | 96 | 15 | 12 | [orientdb.md](orientdb.md) |
| PostgreSQL | 96 | 0 | 0 | [postgresql.md](postgresql.md) |

These numbers describe published query coverage, not successful or comparable
benchmark rows. `benchmark/manifests/adapter_coverage.csv` is authoritative.

Kuzu and OrientDB have repository-relative Python entry points and dedicated
documentation. The other systems currently retain audited query translations
and historical loaders/runners; their `runners/legacy/` scripts contain old
host assumptions and are not formal entry points. New portable runners must
implement `docs/benchmark-contract.md` before replacing that status.

All adapters must load `canonical_full_v1`, record engine versions, and keep
credentials outside command history and source files.

Cross-engine data loading is summarized in `docs/database-loading.md`; formal
execution and result locations are defined in `docs/benchmark-execution.md`.
