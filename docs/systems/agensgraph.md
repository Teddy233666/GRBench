# AgensGraph

AgensGraph publishes 96 main-query translations and 15 Shortest Path
translations. Render and execute the combined historical loader as described
in `docs/database-loading.md`.

Smoke one query after setting `AGENSGRAPH_USERNAME` and
`AGENSGRAPH_DATABASE`:

```sh
agens -X -v ON_ERROR_STOP=1 \
  -U "${AGENSGRAPH_USERNAME:-agens}" \
  -d "${AGENSGRAPH_DATABASE:-grbench}" \
  -f "adapters/agensgraph/queries/Pure_Graph_Queries/25a.sql"
```

Shortest Path SQL is under `adapters/agensgraph/queries/Shortest_Path_Queries/`.
The `3a–3c` translations use the public loader names `Affiliations`,
`affl_assoc_affl`, and `contributed_from`.

Update SQL is copied directly from the retained server source into
`adapters/agensgraph/queries/Update/`. It follows an older lifecycle:
`a/b` directions differ from the current canonical contract and source `3c.sql`
is mapped to canonical query ID `update/3b` only for inventory purposes. These
files are `legacy_adapter`, not comparable implementations.

`adapters/agensgraph/runners/legacy/` is provenance-only. No maintained formal
measurement runner is published.
