# ArangoDB

ArangoDB publishes 96 main and 15 Shortest Path JavaScript/AQL translations.
The retained loader is a mixed historical playbook and is not a one-shot formal
loader; see `docs/database-loading.md`.

Query smoke test:

```sh
timeout "${GRBENCH_TIMEOUT_S}" arangosh \
  --server.endpoint "${ARANGODB_ENDPOINT}" \
  --server.database "${ARANGODB_DATABASE}" \
  --server.username "${ARANGODB_USERNAME}" \
  --javascript.execute "adapters/arangodb/queries/Pure_Graph_Queries/25a.js"
```

Pass `ARANGODB_PASSWORD` through the client's protected configuration or
prompting mechanism. The legacy runners are not contract-compliant.
