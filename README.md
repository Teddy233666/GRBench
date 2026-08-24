# GRBench

GRBench is a cross-model benchmark for relational, graph, and
relational-graph database systems. It publishes one canonical SciSciNet workload
and adapters for AgensGraph, ArangoDB, DuckDB, GrainDB, Kuzu, OrientDB, and
PostgreSQL.

## End-to-End Workflow

```text
data/raw
   -> scripts/data_generation
   -> data/processed/<sf>
   -> adapters/<engine>/loaders
   -> schema + data + indexes in .local/<engine>
   -> adapters/<engine>/queries + runners
   -> .local/results
   -> reviewed results/<engine>
```

Large datasets, databases, generated loader files, logs, caches, and secrets are
never committed.

## Quick Start

Python 3.10 or newer is required for repository tooling.

```sh
git clone https://github.com/Teddy233666/GRBench.git
cd GRBench
cp config/env.example .env
# Edit .env, especially external data paths and database credentials.
set -a; . ./.env; set +a
python3 -m pip install -r requirements-dev.txt
```

### 1. Prepare Data

Place the SciSciNet-v2 Parquet snapshot in `data/raw/sciscinet-v2/`, then:

```sh
python3 -m venv .venv-data
.venv-data/bin/pip install -r requirements-data.txt
.venv-data/bin/python scripts/data_generation/sciscinet/csv_generator.py
.venv-data/bin/python scripts/data_generation/sciscinet/interface.py \
  --data-root data/processed --highest-scale 4
python3 scripts/data_generation/validate_data_profile.py --sf sf10_0
```

Each `data/processed/sf10_N/` directory must contain the same 30 files listed
in `benchmark/manifests/data_profile.csv`. See
[`docs/data-preparation.md`](docs/data-preparation.md).

### 2. Load a Database and Build Indexes

Kuzu example:

```sh
python3 -m venv .venv-kuzu
.venv-kuzu/bin/pip install -r adapters/kuzu/requirements.txt
.venv-kuzu/bin/python adapters/kuzu/loaders/load.py \
  --dataset sf10_0 --threads 8 --strict-rel-copy
.venv-kuzu/bin/python adapters/kuzu/tools/validate_database.py \
  --db-path .local/kuzu/db/db_sf10_0
```

Commands and index behavior for all seven engines are documented in
[`docs/database-loading.md`](docs/database-loading.md).

### 3. Run Queries

```sh
.venv-kuzu/bin/python adapters/kuzu/runners/run_main.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/main.csv \
  --threads 8 --timeout-s 18000 --warmups 1 --repeats 3 --overwrite
```

Formal execution defaults to one warmup, three measured repetitions, an 18,000
second timeout, and same-run median metrics. See
[`docs/benchmark-execution.md`](docs/benchmark-execution.md).

### 4. Validate Repository Artifacts

```sh
python3 tools/generate_manifests.py
python3 tools/audit_query_semantics.py
python3 tools/sanitize_result_paths.py
python3 tools/validate_repository.py --strict-paths
```

### 5. Publish Reviewed Results

New runs stay in `.local/results/<engine>/<sf>/`. Only reviewed artifacts are
copied to `results/<engine>/`; update `results/manifests/source_results.csv` and
regenerate manifests before committing.

## Workload

`benchmark/queries/canonical/` defines 123 query IDs:

- 96 main relational-graph and graph queries;
- 15 Shortest Path queries;
- 12 Update queries named `1a.sql` through `6b.sql`.

Engine translations keep the same IDs under `adapters/<engine>/queries/`.
`Pure_Join_Queries` is retained as an alternate pure relational implementation.

## Repository Layout

- `data/`: raw-data landing documentation, processed SF layout, logical schema.
- `scripts/data_generation/`: Parquet conversion, SF extraction, staging SQL.
- `benchmark/`: canonical workload and deterministic manifests.
- `adapters/<engine>/loaders/`: schema creation, imports, indexes.
- `adapters/<engine>/queries/`: engine-specific query implementation.
- `adapters/<engine>/runners/`: formal or explicitly legacy execution code.
- `config/`: public environment templates without secrets.
- `results/<engine>/`: reviewed, publishable result CSVs.
- `.local/`: ignored databases, generated loaders, logs, caches, temporary runs.
- `docs/`: workflow, deployment, benchmark contract, and maintenance guides.
- `legacy/`: superseded artifacts retained for provenance.

The complete migration map and Git boundary are in
[`docs/repository-layout.md`](docs/repository-layout.md).

## Reproducibility Status

Kuzu and OrientDB have maintained repository-relative formal runners. The other
five adapters currently provide audited query translations, loader evidence,
and execution smoke paths; their historical runners do not yet satisfy the full
measurement contract. Execution success alone does not establish semantic
correctness or cross-system comparability.

## Licensing

Code and documentation are Apache-2.0 (`LICENSE`). Published result tables are
CC BY 4.0 (`RESULTS_LICENSE`). Dataset and DBMS licenses remain separate; see
`THIRD_PARTY_NOTICES.md` and
`docs/development/provenance-and-licensing.md`.
