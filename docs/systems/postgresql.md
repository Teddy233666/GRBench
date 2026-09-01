# PostgreSQL and Apache AGE

PostgreSQL publishes 96 main-query translations and 96 Pure Join SQL variants.
The maintained loader supports plain relational PostgreSQL and Apache AGE
projections for sf10_0 through sf10_4:

```sh
python3 adapters/postgresql/loaders/load.py plan \
  --sf sf10_0 --projection relational --rebuild
python3 adapters/postgresql/loaders/load.py load \
  --sf sf10_0 --projection relational --rebuild
```

AGE additionally requires `load.py prepare-age`. See `docs/database-loading.md`
for server-visible prepared paths, resume manifests, and orphan-edge policy.

Smoke one query:

```sh
PGPASSWORD="${POSTGRES_PASSWORD}" timeout "${GRBENCH_TIMEOUT_S}" \
  psql -X -v ON_ERROR_STOP=1 \
  -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
  -U "${POSTGRES_USERNAME}" -d "${POSTGRES_DATABASE}" \
  -f "adapters/postgresql/queries/Pure_Graph_Queries/25a.sql"
```

The LevelDB/CSV preprocessing helpers require
`adapters/postgresql/loaders/requirements.txt` and system LevelDB headers. No
fully oracle-validated formal runner is published. Retained shell entry points
use current query paths and a corrected hot-session measurement loop:

```sh
adapters/postgresql/runners/legacy/run_main_three_rounds.sh --list
adapters/postgresql/runners/legacy/run_pure_join_three_rounds.sh --list
adapters/postgresql/runners/legacy/run_update_three_rounds.sh --list
adapters/postgresql/runners/legacy/run_update_single_round.sh --list
```

Set `GRBENCH_POSTGRES_UPDATE_PREPARED_ROOT` to the server-visible AGE Update
CSV directory before running either Update entry point. See the runner
directory README for transaction setup/rollback and cgroup measurement rules.
