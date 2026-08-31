# Database Loading and Indexing

Run all commands from the repository root after sourcing an ignored `.env`.
Validate the selected SF before loading:

```sh
python3 scripts/data_generation/validate_data_profile.py --sf sf10_0
```

Database files, generated loader scripts, staging data, and logs belong under
`.local/`; none should be copied into `results/`.

## Loader Matrix

| Engine | Loader location | Schema/import/index status |
| --- | --- | --- |
| AgensGraph | `adapters/agensgraph/loaders/` | Historical combined schema/import templates; graph labels and PK indexes are built during load |
| ArangoDB | `adapters/arangodb/loaders/` | Historical mixed JS/AQL/import playbook; requires manual review before execution |
| DuckDB | `adapters/duckdb/loaders/load_graph.py` | Parameterized table import and DuckPGQ property graph creation |
| GrainDB | `adapters/graindb/loaders/` | Historical combined table/import/property-graph template |
| Kuzu | `adapters/kuzu/loaders/load.py` | Maintained schema, node/relationship import, PK-backed graph storage |
| OrientDB | `adapters/orientdb/loaders/load_orientdb_data.py` | Maintained schema, import manifest, endpoint handling, and explicit indexes |
| PostgreSQL/AGE | `adapters/postgresql/loaders/` | SF-specific historical schema/import templates and preprocessing helpers |

## Render Historical Templates

Templates retain stable provenance aliases such as `legacy_host_data`; render a
local copy before executing one:

```sh
python3 scripts/render_loader.py \
  --template adapters/agensgraph/loaders/load.sql \
  --sf sf10_0 \
  --output .local/generated/loaders/agensgraph-sf10_0.sql
```

The renderer substitutes `data/processed/<sf>`, `.local/prepared/`, and
`.local/update-staging/` paths without changing the tracked template.

## AgensGraph

The retained loader combines extension/schema creation, CSV foreign tables,
graph labels, edge creation, and relational support tables:

```sh
python3 scripts/render_loader.py \
  --template adapters/agensgraph/loaders/load.sql --sf sf10_0 \
  --output .local/generated/loaders/agensgraph-sf10_0.sql
agens -X -v ON_ERROR_STOP=1 -U "${AGENSGRAPH_USERNAME:-agens}" \
  -d "${AGENSGRAPH_DATABASE:-grbench}" \
  -f .local/generated/loaders/agensgraph-sf10_0.sql
```

No separate post-load index script is published; primary-key and graph-label
indexes are created by the statements in the template.

## ArangoDB

`adapters/arangodb/loaders/load.sql` is a historical playbook mixing collection
creation JavaScript, `arangoimport` commands, and AQL edge transformations. It
is retained for provenance but is not a safe one-shot loader. Render it for
inspection only:

```sh
python3 scripts/render_loader.py \
  --template adapters/arangodb/loaders/load.sql --sf sf10_0 \
  --output .local/generated/loaders/arangodb-sf10_0.playbook
```

ArangoDB automatically indexes `_key`, `_from`, and `_to` in document/edge
collections. A maintained portable full-profile loader remains unresolved; do
not claim a formal ArangoDB load from this playbook.

## DuckDB

```sh
python3 -m venv .venv-duckdb
.venv-duckdb/bin/pip install -r requirements-data.txt
.venv-duckdb/bin/python adapters/duckdb/loaders/load_graph.py \
  --sf sf10_0 --data-root data/processed \
  --db .local/duckdb/sciscinet_graph_0.duckdb \
  --threads "${GRBENCH_THREADS}" --memory-limit 64GB
```

The loader creates relational tables and the `sciscinet_graph` DuckPGQ property
graph. No additional index DDL is present in the retained implementation.

## GrainDB

```sh
python3 scripts/render_loader.py \
  --template adapters/graindb/loaders/load.sql --sf sf10_1 \
  --output .local/generated/loaders/graindb-sf10_1.sql
duckdb .local/graindb/sciscinet_graph_1.db \
  < .local/generated/loaders/graindb-sf10_1.sql
```

The template creates tables, imports CSVs, and declares vertices/edges. Its
first historical `exit` line and engine-version assumptions require review;
the command is a compatibility starting point, not a formal loader guarantee.

## Kuzu

```sh
python3 -m venv .venv-kuzu
.venv-kuzu/bin/pip install 'kuzu==0.11.3' 'psutil==7.2.2'
.venv-kuzu/bin/python adapters/kuzu/loaders/load.py \
  --dataset sf10_0 --threads "${GRBENCH_THREADS}" --strict-rel-copy
.venv-kuzu/bin/python adapters/kuzu/loaders/validate_database.py \
  --db-path .local/kuzu/db/db_sf10_0
```

Schema creation precedes node COPY and relationship COPY. Kuzu node primary
keys provide lookup indexes; no separate user index phase exists in this loader.

## OrientDB

```sh
python3 -m venv .venv-orientdb
.venv-orientdb/bin/pip install -r adapters/orientdb/loaders/requirements.txt
.venv-orientdb/bin/python adapters/orientdb/loaders/load_orientdb_data.py \
  --sf sf10_0 --data-root data/processed \
  --db-dir .local/orientdb/databases \
  --update-dir .local/update-staging \
  --query-root adapters/orientdb/queries \
  --update-source-mode derived --rebuild
```

The Java loader creates the schema, imports all configured classes, records
source/loaded/skipped counts and SHA-256 values, then creates configured
NOTUNIQUE property indexes. `ORIENTDB_USERNAME` and `ORIENTDB_PASSWORD` must be
set in the environment.

## PostgreSQL/AGE

Use `load_join1.sql` for the plain relational projection or the SF-specific AGE
templates (`load2.sql`, `load3.sql`, `load4.sql`) when their required
`.local/prepared/<sf>_postgresql/` projection exists:

```sh
python3 scripts/render_loader.py \
  --template adapters/postgresql/loaders/load2.sql --sf sf10_2 \
  --output .local/generated/loaders/postgresql-sf10_2.sql
PGPASSWORD="${POSTGRES_PASSWORD}" psql -X -v ON_ERROR_STOP=1 \
  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USERNAME}" -d "${POSTGRES_DATABASE}" \
  -f .local/generated/loaders/postgresql-sf10_2.sql
```

Primary keys create relational indexes; AGE creates graph-label storage during
`create_vlabel`/`create_elabel`. The numerous Python preprocessing helpers are
preserved but not yet consolidated into one supported preparation interface.
