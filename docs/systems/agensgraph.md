# AgensGraph

AgensGraph publishes 96 main-query translations. Render and execute the
combined historical loader as described in `docs/database-loading.md`.

Smoke one query after setting `AGENSGRAPH_USERNAME` and
`AGENSGRAPH_DATABASE`:

```sh
agens -X -v ON_ERROR_STOP=1 \
  -U "${AGENSGRAPH_USERNAME:-agens}" \
  -d "${AGENSGRAPH_DATABASE:-grbench}" \
  -f "adapters/agensgraph/queries/Pure_Graph_Queries/25a.sql"
```

`adapters/agensgraph/runners/legacy/` is provenance-only. No maintained formal
Shortest Path, Update, or measurement runner is published.
