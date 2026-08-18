# Migration Map

The source aliases below are provenance only. They are not runtime defaults.
`legacy_core`, `legacy_kuzu`, `legacy_orientdb`, and `legacy_host_data` replace
workstation-specific source roots in the public tree.

| Source | Release target | Strategy |
| --- | --- | --- |
| `legacy_core/tasks/sciscinet_tasks/` | `benchmark/queries/canonical/` | canonical snapshot; apply seven approved corrections |
| `legacy_core/tasks/*_task/` | `adapters/<engine>/queries/` | retain latest engine translation; exclude Pure Join copies |
| `legacy_core/data_loader/` | `adapters/<engine>/loaders/` | retain loader source; mark host-specific scripts legacy |
| `legacy_core/test/` | `adapters/<engine>/legacy-runner/` and `results/<engine>/` | separate runner code from selected result snapshots |
| `legacy_core/processor/` | `benchmark/data-generation/processor/` | merge shared SciSciNet generation utilities |
| `legacy_core/data_generator/` | `benchmark/data-generation/generators/` | retain non-SciSciNet generators separately |
| `legacy_kuzu/queries_cypher/` | `adapters/kuzu/queries/` | retain 96 unique main Cypher files |
| `legacy_kuzu/*.py` | `adapters/kuzu/` | keep maintained load/main/shortest/Update entry points |
| `legacy_kuzu/results/` | `results/kuzu/` | publish selected median artifact plus provenance hash |
| `legacy_orientdb/queries/orientdb_sciscinet_tasks_native_graph/` | `adapters/orientdb/queries/` | retain audited 123-query adapter |
| `legacy_orientdb/*.py`, `*.java` | `adapters/orientdb/` | retain loader, worker, oracle, audit, and recovery tools |
| `legacy_orientdb/results/` | `results/orientdb/` | publish completed historical snapshot only; exclude active run |

RelGo is intentionally excluded. Dataset CSVs, DB files, build output, caches,
logs, temporary staging, binaries, and credentials are not migrated.

## Conflict Policy

Same-name files with different semantics are not overwritten. Canonical SQL,
adapter translations, and legacy variants live in separate roots. Exact or
logical Pure Join duplicates are represented by `pure_join_aliases.csv`.
Engine-specific loaders are not merged unless their data transformations are
identical and covered by one schema contract.
