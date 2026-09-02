# Data Loading and Index Construction

Set `GRBENCH_DATA_ROOT` to the directory containing `sf10_0` through `sf10_4`
and create `.local/` before loading. Docker deployment is described in
[`../docker/README.md`](../docker/README.md). Loader paths below are relative to
the repository root.

## PostgreSQL 15.6 and Apache AGE 1.6.0

The maintained loader creates schemas, imports all 30 CSVs, creates primary-key
and endpoint indexes, and records resumable state.

```sh
docker compose --env-file .env -f docker/compose.yml up -d postgresql-age
python3 benchmark/postgresql/loaders/load.py prepare-age \
  --sf sf10_0 --data-root data/processed --orphan-edge-mode fail
python3 benchmark/postgresql/loaders/load.py load \
  --sf sf10_0 --projection age --rebuild \
  --server-prepared-root /data/processed/sf10_0
python3 benchmark/postgresql/loaders/load.py validate \
  --sf sf10_0 --projection age
```

Implementation: `benchmark/postgresql/loaders/`.

## DuckDB 1.2.2 and DuckPGQ 97a0c65

Use an image or environment containing the pinned DuckPGQ extension. The
Python loader creates typed tables and the property graph in one database file.

```sh
python3 benchmark/duckdb/loaders/load_graph.py \
  --sf sf10_0 --data-root data/processed \
  --db .local/duckdb/sf10_0.duckdb --threads 8 --memory-limit 64GB
```

Implementation: `benchmark/duckdb/loaders/load_graph.py`. Index and graph
definitions are created by the loader; the SQL template is retained for
inspection.

## Kuzu 0.11.3

Kuzu is embedded in the Python process. Node primary keys and relationship
topology indexes are created with the schema before `COPY`.

```sh
docker compose --env-file .env -f docker/compose.yml --profile compat up -d kuzu
docker exec grbench-kuzu pip install 'kuzu==0.11.3' 'psutil==7.2.2'
docker exec grbench-kuzu python3 benchmark/kuzu/loaders/load.py \
  --dataset sf10_0 --csv-dir /data/processed/sf10_0 \
  --db-dir .local/kuzu --threads 8 --strict-rel-copy
docker exec grbench-kuzu python3 benchmark/kuzu/loaders/validate_database.py \
  --db-path .local/kuzu/db_sf10_0
```

Implementation: `benchmark/kuzu/loaders/`.

## OrientDB Community 3.2.37

The maintained loader creates the plocal schema, imports vertices and edges,
creates explicit property indexes, and verifies source and loaded counts. Stop
the OrientDB server before opening the same plocal database with the embedded
loader.

```sh
python3 benchmark/orientdb/loaders/load_orientdb_data.py \
  --sf sf10_0 --data-root data/processed \
  --db-dir .local/orientdb-databases \
  --query-root benchmark/orientdb/queries \
  --update-source-mode derived --orphan-edge-mode placeholder --rebuild
```

Set `ORIENTDB_HOME` to the 3.2.37 distribution and `JAVA_HOME` to Java 11.
Implementation: `benchmark/orientdb/loaders/`.

## AgensGraph 2.16

No exact public 2.16 image is pinned by this repository. Build and set
`AGENSGRAPH_IMAGE`, render the server-visible CSV paths, then execute the graph
or relational template with `agens`:

```sh
python3 scripts/render_loader.py \
  --template benchmark/agensgraph/loaders/load.sql --sf sf10_0 \
  --data-root /data/processed --output .local/generated/agensgraph-sf10_0.sql
docker exec -i grbench-agensgraph agens \
  -U "${AGENSGRAPH_USERNAME}" -d "${AGENSGRAPH_DATABASE}" \
  < .local/generated/agensgraph-sf10_0.sql
```

`load.sql` creates vertex/edge labels for the graph projection; `load2.sql` is
the relational projection. No separate audited secondary-index script is
published, so any added indexes must be documented with the run.

## ArangoDB 3.12.4

```sh
docker compose --env-file .env -f docker/compose.yml up -d arangodb
python3 scripts/render_loader.py \
  --template benchmark/arangodb/loaders/load.sql --sf sf10_0 \
  --data-root /data/processed --update-root /data/processed/sf10_0 \
  --output .local/generated/arangodb-sf10_0.txt
```

The retained loader is a compatibility transcript containing both `arangosh`
JavaScript and host-side `arangoimport` commands. Execute those sections in
their respective clients after review. ArangoDB automatically creates edge
indexes; no additional audited index script is currently published. This is
not yet a one-command maintained loader.

## GRainDB be901b3

Build the paper commit into `GRAINDB_IMAGE` and prepare its cleaned/RID-mapped
CSV projection. Render and execute the template with that image's CLI:

```sh
python3 scripts/render_loader.py \
  --template benchmark/graindb/loaders/load.sql --sf sf10_0 \
  --data-root data/processed --prepared-root .local/prepared/graindb \
  --output .local/generated/graindb-sf10_0.sql
docker exec -i grbench-graindb duckdb_cli .local/graindb/sf10_0.db \
  < .local/generated/graindb-sf10_0.sql
```

The template creates the required tables. A separate audited RID/index build
step and the cleaned projection generator are not included, so this remains a
compatibility workflow rather than a complete public loader.
