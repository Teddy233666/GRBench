# ArangoDB

ArangoDB publishes 96 main, 96 Pure Join, and 15 Shortest Path JavaScript/AQL translations.
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

Of the Pure Join files, 72 pass the static semantic audit. The other 24 are the
requested authoritative legacy versions and remain `legacy_unverified`; see
`docs/development/pure-join-audit.md`.

Retained Update files are under `adapters/arangodb/queries/Update/`. Their
filenames follow the canonical direction (`a` deletes, `b` restores or inserts),
including the historical `3c.js` to `3a.js` rename. The query bodies remain
unaudited and incomplete, so Update coverage is still `not_implemented`.
