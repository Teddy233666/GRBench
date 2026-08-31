# PostgreSQL and Apache AGE

PostgreSQL publishes 96 main-query translations and 96 Pure Join SQL variants.
Historical loaders include a plain relational projection and SF-specific AGE projections. Render paths with
`scripts/render_loader.py`; see `docs/database-loading.md`.

Smoke one query:

```sh
PGPASSWORD="${POSTGRES_PASSWORD}" timeout "${GRBENCH_TIMEOUT_S}" \
  psql -X -v ON_ERROR_STOP=1 \
  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USERNAME}" -d "${POSTGRES_DATABASE}" \
  -f "adapters/postgresql/queries/Pure_Graph_Queries/25a.sql"
```

The LevelDB/CSV preprocessing helpers require
`adapters/postgresql/loaders/requirements.txt` and system LevelDB headers. No maintained
formal Shortest Path or Update runner is published.
