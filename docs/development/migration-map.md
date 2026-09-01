# Migration Map

The source aliases below are provenance only. They are not runtime defaults.
`legacy_core`, `legacy_kuzu`, `legacy_orientdb`, and `legacy_host_data` replace
workstation-specific source roots in the public tree.

| Source | Release target | Strategy |
| --- | --- | --- |
| `legacy_core/tasks/sciscinet_tasks/` | `benchmark/queries/canonical/` | canonical snapshot; apply seven approved corrections |
| `legacy_core/tasks/*_task/` | `adapters/<engine>/queries/` | retain latest engine translation, including audited Pure Join physical variants |
| `legacy_core/data_loader/` | `adapters/<engine>/loaders/` | retain loader source; mark host-specific scripts legacy |
| `legacy_core/test/` | `adapters/<engine>/runners/legacy/` and `results/<engine>/` | separate runner code from selected result snapshots |
| `legacy_core/test/postgresql/*.sh` | `adapters/postgresql/runners/legacy/run_*_round*.sh` | retain hot-session shell behavior with descriptive suite/run-count names and corrected paths |
| `legacy_core/processor/` | `scripts/data_generation/sciscinet/` | merge shared SciSciNet generation utilities |
| `legacy_core/data_generator/` | `scripts/data_generation/auxiliary/` | retain non-SciSciNet generators separately |
| `legacy_kuzu/queries_cypher/` | `adapters/kuzu/queries/` | retain 96 unique main Cypher files; record byte-identical Pure Join files without copying them |
| `legacy_kuzu/*.py` | `adapters/kuzu/loaders/` and `runners/` | separate maintained load, benchmark, test, and audit entry points |
| `legacy_kuzu/results/` | `results/kuzu/` | publish selected median artifact plus provenance hash |
| `legacy_orientdb/queries/orientdb_sciscinet_tasks_native_graph/` | `adapters/orientdb/queries/` | retain the audited 219-query adapter, including corrected Pure Join variants |
| `legacy_orientdb/*.py`, `*.java` | `adapters/orientdb/loaders/`, `queries/`, and `runners/` | separate loader, query rewrite, worker, oracle, audit, and recovery roles |
| `legacy_orientdb/results/` | `results/orientdb/` | publish completed historical snapshot only; exclude active run |

RelGo is intentionally excluded. Dataset CSVs, DB files, build output, caches,
logs, temporary staging, binaries, and credentials are not migrated.

## Conflict Policy

Same-name files with different semantics are not overwritten. Canonical SQL,
adapter translations, and legacy variants live in separate roots. Pure Join
physical variants are represented by `pure_join_variants.csv`; only Kuzu's
byte-identical Cypher copies are excluded from execution.
Engine-specific loaders are not merged unless their data transformations are
identical and covered by one schema contract.
