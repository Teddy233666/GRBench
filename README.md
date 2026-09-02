# GRBench

GRBench is the artifact for **GRBench: A Comprehensive Benchmark Evaluation
for Graph-relational Data Management** ([arXiv:2608.31027v1](https://arxiv.org/abs/2608.31027)).
It evaluates graph-relational query processing, shortest paths, graph updates,
and relational equivalents over five SciSciNet-v2 scale factors.

## Evaluated Systems

| System | Version used in the paper |
| --- | --- |
| PostgreSQL + Apache AGE | PostgreSQL 15.6 + AGE 1.6.0 |
| DuckDB + DuckPGQ | DuckDB 1.2.2 + DuckPGQ commit `97a0c65` |
| ArangoDB | 3.12.4 |
| AgensGraph | 2.16 |
| OrientDB Community | 3.2.37 |
| GRainDB | commit `be901b3` |
| Kuzu | 0.11.3 |

Repository assets are grouped by system:

```text
benchmark/<system>/
  loaders/   schema creation, import, and index construction
  queries/   H, G, S, RH, RG, and U query implementations
  runners/   execution and resource-measurement entry points
```


## 1. Data Preparation

GRBench does not redistribute SciSciNet-v2. Place the original Parquet files
under `data/raw/sciscinet-v2/`. Data conversion and deterministic scale-factor
extraction are implemented in `scripts/data_generation/sciscinet/`; the schema
and 30-file inventory are defined in `data/schema/sciscinet.py`.

```sh
git clone https://github.com/Teddy233666/GRBench.git
cd GRBench
cp config/env.example .env
set -a; . ./.env; set +a

python3 -m venv .venv-data
.venv-data/bin/pip install -r requirements-data.txt
.venv-data/bin/python scripts/data_generation/sciscinet/csv_generator.py
.venv-data/bin/python scripts/data_generation/sciscinet/interface.py \
  --data-root data/processed --highest-scale 4
python3 scripts/data_generation/validate_data_profile.py \
  --data-root data/processed --sf sf10_0
```

The highest scale is written to `data/processed/sf10_4/`; extraction writes
`sf10_3/` through `sf10_0/` beside it. Update support data is defined by
`scripts/data_generation/derive_update_staging.sql` and belongs under
`.local/<system>/staging/`. See [data preparation](docs/data-preparation.md).

### Table Cardinalities

Counts are logical CSV records excluding headers. sf10_0-sf10_3 counts come
from source-row-verified loader manifests; sf10_4 counts come from Parquet
metadata. The machine-readable table, including logical object names, is
[`docs/table-cardinalities.csv`](docs/table-cardinalities.csv); its counting
method and source-vs-loaded distinction are documented in
[`docs/table-cardinalities.md`](docs/table-cardinalities.md).

| CSV table | sf10_0 | sf10_1 | sf10_2 | sf10_3 | sf10_4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `hit_papers_level0.csv` | 56,936 | 569,723 | 5,699,580 | 57,009,573 | 570,263,651 |
| `hit_papers_level1.csv` | 70,002 | 702,805 | 7,011,698 | 70,132,137 | 701,627,506 |
| `normalized_citations_level0.csv` | 56,936 | 569,723 | 5,699,580 | 57,009,573 | 570,263,651 |
| `normalized_citations_level1.csv` | 70,002 | 702,805 | 7,011,698 | 70,132,137 | 701,627,506 |
| `sciscinet_affiliations.csv` | 13,779 | 36,202 | 64,288 | 88,007 | 110,553 |
| `sciscinet_affl_assoc_affl.csv` | 1,027 | 2,567 | 6,325 | 15,695 | 39,239 |
| `sciscinet_author_affiliation.csv` | 46,075 | 460,751 | 4,607,517 | 46,075,174 | 460,751,741 |
| `sciscinet_author_details.csv` | 74,172 | 644,529 | 4,067,799 | 18,009,725 | 100,418,971 |
| `sciscinet_authors.csv` | 74,172 | 644,529 | 4,067,799 | 18,009,725 | 100,418,971 |
| `sciscinet_authors_paperid.csv` | 77,298 | 772,984 | 7,729,844 | 77,298,443 | 772,984,433 |
| `sciscinet_clinicaltrials_metadata.csv` | 19,974 | 66,666 | 122,234 | 172,286 | 273,269 |
| `sciscinet_fields.csv` | 303 | 303 | 303 | 303 | 303 |
| `sciscinet_link_clinicaltrials.csv` | 3,196 | 16,539 | 55,132 | 183,776 | 612,587 |
| `sciscinet_link_newsfeed.csv` | 1,787 | 11,278 | 56,393 | 281,968 | 1,409,842 |
| `sciscinet_link_nih.csv` | 5,808 | 50,369 | 261,873 | 1,309,368 | 6,546,840 |
| `sciscinet_link_nobellaureates.csv` | 2,335 | 5,512 | 13,955 | 34,936 | 87,316 |
| `sciscinet_link_nsf.csv` | 1,422 | 12,477 | 70,774 | 353,871 | 1,769,355 |
| `sciscinet_link_patents.csv` | 4,232 | 44,770 | 462,040 | 4,731,461 | 47,844,586 |
| `sciscinet_link_twitter.csv` | 5,584 | 55,846 | 558,465 | 5,584,655 | 55,846,550 |
| `sciscinet_newsfeed_metadata.csv` | 2,207 | 11,423 | 56,982 | 284,333 | 1,409,842 |
| `sciscinet_nih_metadata.csv` | 16,770 | 59,272 | 147,812 | 302,800 | 533,653 |
| `sciscinet_nsf_metadata.csv` | 10,902 | 39,309 | 112,345 | 261,040 | 459,837 |
| `sciscinet_paper_author_affiliation.csv` | 46,075 | 460,751 | 4,607,517 | 46,075,174 | 772,984,433 |
| `sciscinet_paperdetails.csv` | 488,843 | 4,498,734 | 30,130,205 | 84,352,557 | 249,803,279 |
| `sciscinet_paperfields.csv` | 127,189 | 1,271,891 | 12,718,911 | 127,189,115 | 1,271,891,157 |
| `sciscinet_paperrefs.csv` | 249,061 | 2,492,361 | 24,937,755 | 249,436,785 | 2,494,545,461 |
| `sciscinet_papers.csv` | 488,843 | 4,498,734 | 30,130,205 | 84,352,557 | 249,803,279 |
| `sciscinet_papersources.csv` | 20,428 | 204,399 | 2,041,299 | 20,408,396 | 204,111,441 |
| `sciscinet_sources.csv` | 2,070 | 7,084 | 23,403 | 78,448 | 260,811 |
| `sciscinet_twitter_metadata.csv` | 6,100 | 60,321 | 596,822 | 5,950,578 | 59,593,281 |

## 2. Docker Deployment, Import, and Indexes

Set non-empty passwords in `.env`, then start the pinned server images:

```sh
docker compose --env-file .env -f docker/compose.yml up -d \
  postgresql-age arangodb orientdb
```

AgensGraph 2.16, DuckPGQ `97a0c65`, and GRainDB `be901b3` require custom exact
images; the compatibility profiles must not be reported as paper-equivalent
without version verification. See [Docker environments](docker/README.md).

Maintained import examples:

```sh
# PostgreSQL/AGE: prepare endpoint IDs, load, and build indexes.
python3 benchmark/postgresql/loaders/load.py prepare-age \
  --sf sf10_0 --data-root data/processed --orphan-edge-mode fail
python3 benchmark/postgresql/loaders/load.py load \
  --sf sf10_0 --projection age --rebuild

# Kuzu: create schema/PK indexes and import nodes and relationships.
python3 benchmark/kuzu/loaders/load.py \
  --dataset sf10_0 --csv-dir data/processed/sf10_0 \
  --db-dir .local/kuzu --threads 8 --strict-rel-copy

# OrientDB: create plocal schema, import, and build property indexes.
python3 benchmark/orientdb/loaders/load_orientdb_data.py \
  --sf sf10_0 --data-root data/processed \
  --db-dir .local/orientdb-databases \
  --query-root benchmark/orientdb/queries \
  --update-source-mode derived --orphan-edge-mode placeholder --rebuild

# DuckDB/DuckPGQ: create typed tables and the property graph.
python3 benchmark/duckdb/loaders/load_graph.py \
  --sf sf10_0 --data-root data/processed \
  --db .local/duckdb/sf10_0.duckdb --threads 8 --memory-limit 64GB
```

AgensGraph and GRainDB use rendered SQL templates; ArangoDB retains a mixed
`arangosh`/`arangoimport` compatibility transcript. Exact commands, code paths,
index behavior, and current gaps for all seven systems are in
[data loading](docs/data-loading.md).

## 3. Query Execution, Monitoring, and Results

Queries live under `benchmark/<system>/queries/`. Filenames match the paper:

| Series | IDs | Purpose |
| --- | --- | --- |
| H | `H1a`-`H24c` | Graph-relational hybrid queries |
| G | `G1a`-`G8c` | Pure graph queries |
| S | `S1a`-`S5c` | Shortest-path queries |
| RH/RG | `RH1a`-`RH24c`, `RG1a`-`RG8c` | Relational equivalents |
| U | `U1a`-`U6b` | Delete/restore update pairs |

Six systems publish 219 query files. Kuzu publishes 123 logical H/G/S/U
queries plus six zero-length S-series helper templates; its historical
relational-equivalent files were byte-identical to H/G Cypher and are omitted
rather than measured twice.

Formal settings are one warmup, three measured repetitions, an 18,000-second
timeout, and resource sampling from the database process tree. Examples:

```sh
python3 benchmark/kuzu/runners/run_main.py \
  --dataset sf10_0 --results .local/results/kuzu/sf10_0/main.csv \
  --threads 8 --timeout-s 18000 --sample-hz 100 \
  --warmups 1 --repeats 3 --overwrite

python3 benchmark/orientdb/runners/run_orientdb.py \
  --sf sf10_0 --query-root benchmark/orientdb/queries \
  --source-query-root benchmark/duckdb/queries \
  --db-dir .local/orientdb-databases \
  --expected-results .local/orientdb-oracle.json \
  --execution-mode warm --timeout 18000 --warmup-runs 1 --runs 3 \
  --resource-sample-interval 0.01 \
  --results-dir .local/results/orientdb/sf10_0 --preflight-only

benchmark/postgresql/runners/run_main_three_rounds.sh
benchmark/postgresql/runners/run_relational_three_rounds.sh
benchmark/postgresql/runners/run_update_three_rounds.sh
```

Output belongs
under `.local/results/<system>/<sf>/`. Formal CSV rows retain query ID, status,
elapsed time, CPU peak/average, memory peak/average, and result/error. Detailed commands,
compatibility-runner coverage, and exact output files are in
[query execution](docs/query-execution.md).

## Repository and Publication Boundaries

- `data/raw/` and `data/processed/`: ignored source and generated datasets.
- `scripts/data_generation/`: conversion, SF extraction, and Update staging.
- `benchmark/<system>/`: loaders, queries, and runners owned by one system.
- `docker/`: public container definitions; persistent state stays in `.local/`.
- `docs/`: workflow details, paper ID mapping, and cardinalities.
- `.local/`: ignored databases, generated loaders, logs, caches, and results.


Code and documentation are Apache-2.0 (`LICENSE`). SciSciNet-v2 and database
systems retain their own licenses; see `THIRD_PARTY_NOTICES.md`.
