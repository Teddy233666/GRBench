# DuckDB

DuckDB executes the 123 canonical SQL files directly. Load one SF with:

```sh
python3 adapters/duckdb/loaders/load_graph.py \
  --sf sf10_0 --data-root data/processed \
  --db .local/duckdb/sciscinet_graph_0.duckdb \
  --threads 8 --memory-limit 64GB
```

Smoke one canonical query:

```sh
timeout "${GRBENCH_TIMEOUT_S}" duckdb \
  .local/duckdb/sciscinet_graph_0.duckdb \
  < "benchmark/queries/canonical/Pure_Graph_Queries/25a.sql"
```

The loader installs DuckPGQ from the community extension repository. The
historical shell runner does not implement the current formal metric contract.
