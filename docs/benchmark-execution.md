# Benchmark Execution

## Workload Layout

`benchmark/queries/canonical/` is authoritative:

- three main categories contain 96 SQL files (`1a.sql` through `32c.sql`);
- `Pure_Join_Queries/` contains 96 alternate relational implementations;
- `Shortest_Path_Queries/` contains 15 files (`1a.sql` through `5c.sql`);
- `update/Update/` contains 12 files (`1a.sql` through `6b.sql`).

Engine translations live under `adapters/<engine>/queries/` with the same IDs.
Kuzu generates Shortest Path and Update Cypher at runtime. Adapter coverage is
recorded in `benchmark/manifests/adapter_coverage.csv`.

Pure Join is a physical variant, not a second logical query definition. Kuzu
skips it because all 96 historical Cypher files are byte-identical to main.
ArangoDB publishes all 96 files: 72 are statically audited and 24 requested
legacy AQL files are explicitly `legacy_unverified` because their known
semantic signatures do not match canonical.

## Formal Parameters

The default contract is:

```text
threads=8
timeout=18000 seconds per query
warmups=1
measured repetitions=3
resource sample interval=0.01 seconds
```

The measured run with median elapsed time supplies every reported metric. CPU
and RSS are not independently median-aggregated. Update setup, compensation,
validation, recovery, and database-copy time are outside elapsed time.

Configure defaults through `config/env.example`. New run output belongs under
`.local/results/<engine>/<sf>/`; logs belong under `.local/logs/<engine>/<sf>/`.
Move a result into `results/<engine>/` only after provenance and comparability
review, then regenerate `results/manifests/`.

## Kuzu Formal Runners

```sh
.venv-kuzu/bin/python adapters/kuzu/runners/run_main.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/main.csv \
  --threads 8 --timeout-s 18000 --warmups 1 --repeats 3 \
  --skip-pure-join --overwrite

.venv-kuzu/bin/python adapters/kuzu/runners/run_shortest.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/shortest.csv \
  --threads 8 --sample-hz 100 --warmups 1 --repeats 3 --overwrite

.venv-kuzu/bin/python adapters/kuzu/runners/run_update.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/update.csv \
  --threads 8 --sample-hz 100 --warmups 1 --repeats 3 \
  --isolate-copy --overwrite
```

## OrientDB Formal Runner

Generate/validate an independent DuckDB oracle before a data-loaded run, then:

```sh
.venv-orientdb/bin/python adapters/orientdb/runners/tools/audit_benchmark_contract.py
.venv-orientdb/bin/python adapters/orientdb/runners/run_orientdb.py \
  --sf sf10_0 --db-dir .local/orientdb/databases \
  --data-root data/processed \
  --query-root adapters/orientdb/queries \
  --source-query-root benchmark/queries/canonical \
  --expected-results .local/orientdb-oracle.json \
  --load-mode canonical_full_v1_data_loaded \
  --execution-mode warm --timeout 18000 \
  --warmup-runs 1 --runs 3 --resource-sample-interval 0.01 \
  --results-dir .local/results/orientdb/sf10_0
```

Run the same command with `--preflight-only` first. Never open one plocal
database from two processes.

## Static and Legacy Adapters

AgensGraph, ArangoDB, DuckDB, GrainDB, and PostgreSQL currently publish query
translations but do not have a maintained runner satisfying the complete
measurement contract. AgensGraph's Update files are explicitly legacy and do
not preserve the current Update lifecycle. Scripts under
`adapters/<engine>/runners/legacy/` are preserved for provenance.

For an execution smoke test, invoke the native client against one adapter query,
for example:

```sh
timeout "${GRBENCH_TIMEOUT_S}" psql -X \
  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USERNAME}" -d "${POSTGRES_DATABASE}" \
  -f "adapters/postgresql/queries/Pure_Graph_Queries/25a.sql"

timeout "${GRBENCH_TIMEOUT_S}" psql -X \
  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USERNAME}" -d "${POSTGRES_DATABASE}" \
  -f "adapters/postgresql/queries/Pure_Join_Queries/Pure_Graph_Queries/25a.sql"

timeout "${GRBENCH_TIMEOUT_S}" arangosh \
  --server.endpoint "${ARANGODB_ENDPOINT}" \
  --server.database "${ARANGODB_DATABASE}" \
  --server.username "${ARANGODB_USERNAME}" \
  --javascript.execute "adapters/arangodb/queries/Pure_Graph_Queries/25a.js"

timeout "${GRBENCH_TIMEOUT_S}" duckdb \
  .local/duckdb/sciscinet_graph_0.duckdb \
  < "adapters/duckdb/queries/Pure_Graph_Queries/25a.sql"
```

These smoke commands do not produce comparable Benchmark metrics. Implement a
contract-compliant warm-session runner before promoting results from those five
systems.
