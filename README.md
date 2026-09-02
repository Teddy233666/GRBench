# GRBench

GRBench is a cross-model SciSciNet benchmark for AgensGraph, ArangoDB,
DuckDB, GrainDB, Kuzu, OrientDB, and PostgreSQL/Apache AGE. Each database owns
its complete implementation under one directory:

```text
benchmark/<database>/
  loaders/   schema creation, data import, and index construction
  queries/   database-specific Main, Pure Join, Shortest Path, and Update queries
  runners/   benchmark entry points and measurement helpers
```

Large datasets, database files, logs, caches, credentials, and generated result
files are local artifacts and are not committed.

## Quick Start

Python 3.10 or newer is required for the Python loaders and runners.

```sh
git clone https://github.com/Teddy233666/GRBench.git
cd GRBench
cp config/env.example .env
set -a; . ./.env; set +a
python3 -m pip install -r requirements-dev.txt
```

### Prepare Data

Place the external SciSciNet-v2 Parquet snapshot under
`data/raw/sciscinet-v2/`, then generate the highest scale and derive lower
scale factors:

```sh
python3 -m venv .venv-data
.venv-data/bin/pip install -r requirements-data.txt
.venv-data/bin/python scripts/data_generation/sciscinet/csv_generator.py
.venv-data/bin/python scripts/data_generation/sciscinet/interface.py \
  --data-root data/processed --highest-scale 4
python3 scripts/data_generation/validate_data_profile.py \
  --data-root data/processed --sf sf10_0
```

Each `data/processed/sf10_N/` directory must contain the 30 CSV files defined
by `data/schema/sciscinet.py`. See [data-preparation.md](docs/data-preparation.md).

### Load and Run

Kuzu example:

```sh
python3 -m venv .venv-kuzu
.venv-kuzu/bin/pip install 'kuzu==0.11.3' 'psutil==7.2.2'
.venv-kuzu/bin/python benchmark/kuzu/loaders/load.py \
  --dataset sf10_0 --threads 8 --strict-rel-copy
.venv-kuzu/bin/python benchmark/kuzu/runners/run_main.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/main.csv \
  --threads 8 --timeout-s 18000 --warmups 1 --repeats 3 --overwrite
```

PostgreSQL/AGE loader and runner commands are documented in
[its loader README](benchmark/postgresql/loaders/README.md) and
[runner README](benchmark/postgresql/runners/README.md). Other database
directories expose their available loader and runner entry points directly.

## Query Inventory

AgensGraph, ArangoDB, DuckDB, GrainDB, OrientDB, and PostgreSQL each publish
219 query files: 96 Main, 96 Pure Join, 15 Shortest Path, and 12 Update. Kuzu
publishes 123 logical queries and six additional zero-length path helper
templates. Kuzu omits Pure Join because those historical Cypher files were
byte-identical to its Main queries.

The same query ID denotes the same benchmark task across database directories.
Engine-specific syntax, physical graph modeling, and path expansion remain in
the owning database directory.

## Local Outputs

Use `.local/<database>/` for database state, generated staging files, logs, and
results. Raw and processed datasets remain under `data/raw/` and
`data/processed/` and are ignored by Git. This repository currently publishes
benchmark implementations, not result snapshots.

## Validation

GitHub Actions validates Python compilation, the seven-directory layout, query
inventory counts, PostgreSQL runner inventories, shell syntax, ArangoDB
JavaScript syntax, cache hygiene, and file-size limits. The workflow does not
perform data loading or full benchmark execution.

## Reproducibility Status

Static validation does not prove live DBMS execution or cross-system result
equivalence. Record the DBMS version, scale factor, timeout, repetition count,
resource sampling method, query status, and result oracle when publishing a
benchmark run.

## Licensing

Code and documentation are Apache-2.0 (`LICENSE`). Database systems and
SciSciNet data retain their own licenses; see `THIRD_PARTY_NOTICES.md`.
