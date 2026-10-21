# Query Execution and Results

Queries are stored under `benchmark/<database>/queries/`. Filenames use the
paper's H, G, S, RH, RG, and U series; the six relational-capable systems also
provide S expressions under `Relational_Equivalent_Queries/Shortest_Path_Queries/`.
See
[`query-naming.md`](query-naming.md). Run from the repository root with a
per-query timeout of 18,000 seconds, one warmup, and three measured repetitions.

## Maintained Runners

### Kuzu

```sh
python3 benchmark/kuzu/runners/run_main.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/main.csv \
  --threads 8 --timeout-s 18000 --sample-hz 100 \
  --warmups 1 --repeats 3 --overwrite
python3 benchmark/kuzu/runners/run_shortest.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/shortest.csv \
  --sample-hz 100 --warmups 1 --repeats 3 --overwrite
python3 benchmark/kuzu/runners/run_update.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/update.csv \
  --sample-hz 100 --warmups 1 --repeats 3 --isolate-copy --overwrite
```

Each CSV contains query ID, status, elapsed time, CPU peak/average, memory
peak/average, sample count, result/error text, and execution provenance. The
selected row is one observed median-elapsed run; metrics are not independently
combined across repetitions.

### OrientDB

Generate an independent expected-result oracle, then preflight and run:

```sh
python3 benchmark/orientdb/runners/run_orientdb.py \
  --sf sf10_0 --query-root benchmark/orientdb/queries \
  --source-query-root benchmark/duckdb/queries \
  --db-dir .local/orientdb-databases --data-root data/processed \
  --expected-results .local/orientdb-oracle.json \
  --load-mode canonical_full_v1_data_loaded --execution-mode warm \
  --timeout 18000 --warmup-runs 1 --runs 3 \
  --resource-sample-interval 0.01 \
  --results-dir .local/results/orientdb/sf10_0 --preflight-only
# Remove --preflight-only only after the contract check passes.
```

Outputs include `all_results.csv`, per-SF `per_query.csv`, metadata, summaries,
and logs. CPU/RSS are sampled from the embedded worker process tree; correctness
and comparison eligibility are recorded separately.

### PostgreSQL and AGE

```sh
benchmark/postgresql/runners/run_main_three_rounds.sh
benchmark/postgresql/runners/run_relational_three_rounds.sh
benchmark/postgresql/runners/run_update_three_rounds.sh
```

Defaults are `.local/results/postgresql/*_three_rounds.csv`, including
`relational_three_rounds.csv` for RH/RG. Rows contain the
paper query filename, elapsed time, CPU peak/average, RSS peak/average, sample
count, selected repetition, status, result, and error. Set
`POSTGRES_CGROUP_PATH` only for a dedicated container cgroup.

## Compatibility Runners

| System | Command | Coverage | Default output |
| --- | --- | --- | --- |
| AgensGraph | `benchmark/agensgraph/runners/run_update_subset_once.sh` | U4-U6 subset, once | `.local/results/agensgraph/update_subset.csv` |
| ArangoDB | `benchmark/arangodb/runners/run_relational_three_rounds.sh` | RH/RG, three rounds | `.local/results/arangodb/relational_three_rounds.csv` |
| DuckDB | `benchmark/duckdb/runners/run_update_once.sh` | U-series, once | `.local/results/duckdb/update_once.csv` |
| GRainDB | `benchmark/graindb/runners/run_update_once.sh` | U-series, once | `.local/results/graindb/update.csv` |
| GRainDB | `benchmark/graindb/runners/run_h1_h3_three_rounds.sh` | H1-H3, three rounds | `.local/results/graindb/main_subset.csv` |

These scripts record elapsed time and, except the AgensGraph subset runner,
sample CPU and memory. They do not all implement the paper's complete workload,
oracle validation, or identical isolation policy, so their output must not be
presented as directly comparable without additional validation.

All result files, monitor samples, logs, database copies, and temporary files
belong under `.local/` and are excluded from Git.
