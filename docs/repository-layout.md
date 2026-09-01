# Repository Layout

GRBench is organized in execution order: prepare data, load an engine, build
its indexes, run queries, and publish selected results.

## Directory Responsibilities

```text
data/
  raw/                    External source snapshots; data ignored by Git
  processed/<sf>/         Canonical 30-CSV SF datasets; data ignored by Git
  schema/                 Engine-independent logical schema
scripts/
  data_generation/        Parquet conversion, SF extraction, staging SQL
  render_loader.py        Render legacy loader aliases into .local paths
benchmark/
  queries/canonical/      Authoritative 219-query workload
  manifests/              Query, data, adapter, lifecycle, and variant manifests
adapters/<engine>/
  loaders/                Schema creation, import, and index code
  queries/                Engine-specific query translations
  runners/                Maintained or explicitly legacy execution code
config/                   Public environment templates
results/<engine>/         Reviewed result artifacts intended for publication
.local/                   Databases, generated loaders, staging, logs, caches
docs/                     Data, loading, execution, and maintenance guides
legacy/                   Superseded workload artifacts retained for provenance
```

## Path Migration

| Old path | New path | Reason |
| --- | --- | --- |
| `benchmark/data-generation/processor/` | `scripts/data_generation/sciscinet/` | SF generation is an executable workflow, not workload definition |
| `benchmark/data-generation/generators/` | `scripts/data_generation/auxiliary/` | Separate non-canonical IMDb/MOOCCube utilities |
| `benchmark/schema/sciscinet.py` | `data/schema/sciscinet.py` | Keep the data contract beside raw/processed layout |
| `benchmark/setup/derive_update_staging.sql` | `scripts/data_generation/derive_update_staging.sql` | Update staging is data preparation |
| `adapters/*/legacy-runner/` | `adapters/*/runners/legacy/` | Put all execution code under one predictable path |
| `adapters/kuzu/load.py` | `adapters/kuzu/loaders/load.py` | Separate loading from query execution |
| `adapters/kuzu/run_*.py` | `adapters/kuzu/runners/run_*.py` | Standard runner location |
| `adapters/kuzu/measurement.py` | `adapters/kuzu/runners/measurement.py` | Runner-internal measurement module |
| `adapters/orientdb/load_orientdb_data.py` | `adapters/orientdb/loaders/load_orientdb_data.py` | Standard loader location |
| `adapters/orientdb/OrientDbCsvLoader.java` | `adapters/orientdb/loaders/OrientDbCsvLoader.java` | Java loader implementation follows its Python entry point |
| `adapters/orientdb/run_orientdb.py` | `adapters/orientdb/runners/run_orientdb.py` | Standard runner location |
| `adapters/orientdb/OrientDbBenchmarkWorker.java` | `adapters/orientdb/runners/OrientDbBenchmarkWorker.java` | Worker is private to the runner interface |
| Kuzu adapter-level tests/tools/docs | `loaders/`, `queries/`, or `runners/` by ownership | Keep every adapter root limited to three workflow directories |
| OrientDB shared/tools/tests/docs/legacy | `loaders/`, `queries/`, or `runners/` by ownership | Co-locate support code with the interface it serves |
| PostgreSQL root requirements and legacy Update | `loaders/requirements.txt`, `queries/legacy/` | Keep dependencies and historical queries under their workflow phase |
| `tasks/*/Pure_Join_Queries/` | `benchmark/queries/canonical/Pure_Join_Queries/` and `adapters/*/queries/Pure_Join_Queries/` | Preserve alternate relational execution as a separate physical workload |

Canonical query paths and `results/<engine>/` are intentionally unchanged to
preserve query IDs, result provenance, and the result layout introduced before
this migration.

## Preserved Legacy Material

The following files remain because their behavior or provenance may still be
needed:

- `adapters/*/runners/legacy/`: historical measurement scripts with old
  assumptions; not formal entry points.
- `legacy/update-v0/` and `adapters/*/legacy/update-v0/`: superseded Update
  variants.

Do not delete or promote these files without a semantic and live execution
audit.

## Git Boundary

Commit source, queries, public templates, documentation, manifests, and reviewed
results. Do not commit files below `data/raw/`, `data/processed/`, or `.local/`,
except their tracked README files. Database files, generated loader renderings,
logs, temporary output, caches, secrets, model files, and archives are ignored.
