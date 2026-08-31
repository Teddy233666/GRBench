# GrainDB

GrainDB publishes 96 main, 96 Pure Join, and 12 Update translations. Render the
retained loader into `.local/generated/loaders/` before use; see
`docs/database-loading.md`.

Smoke one query with the GrainDB-compatible CLI:

```sh
timeout "${GRBENCH_TIMEOUT_S}" "${GRAINDB_CLI:-duckdb}" \
  .local/graindb/sciscinet_graph_1.db \
  < "adapters/graindb/queries/Pure_Graph_Queries/25a.sql"
```

Update support tables come from
`scripts/data_generation/derive_update_staging.sql`. The loader and legacy
runner require a live compatibility audit before formal use.
