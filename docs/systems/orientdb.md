# OrientDB

OrientDB requires Java 11 and OrientDB Community 3.2.37. Set `JAVA_HOME`,
`ORIENTDB_HOME`, `GRBENCH_DATA_ROOT`, and `GRBENCH_UPDATE_DIR` as shown in
`config/env.example`, then install Python dependencies:

```sh
python3 -m venv .venv-orientdb
.venv-orientdb/bin/pip install -r adapters/orientdb/loaders/requirements.txt
```

Set `ORIENTDB_USERNAME` and `ORIENTDB_PASSWORD` in the process environment or an
ignored local env file. The password is required and is never accepted as a CLI
argument. Load one scale factor with explicit public paths:

```sh
.venv-orientdb/bin/python adapters/orientdb/loaders/load_orientdb_data.py \
  --sf sf10_0 \
  --data-root "${GRBENCH_DATA_ROOT}" \
  --db-dir "${GRBENCH_ORIENTDB_DB_ROOT}" \
  --update-dir "${GRBENCH_UPDATE_DIR}" \
  --query-root adapters/orientdb/queries \
  --update-source-mode derived \
  --rebuild
```

Provide the required independent oracle under `.local/`, then run preflight and
the warm benchmark:

```sh
.venv-orientdb/bin/python adapters/orientdb/runners/run_orientdb.py \
  --sf sf10_0 \
  --data-root "${GRBENCH_DATA_ROOT}" \
  --db-dir "${GRBENCH_ORIENTDB_DB_ROOT}" \
  --query-root adapters/orientdb/queries \
  --source-query-root benchmark/queries/canonical \
  --expected-results "${GRBENCH_ORIENTDB_ORACLE}" \
  --load-mode canonical_full_v1_data_loaded \
  --execution-mode warm --runs 3 --warmup-runs 1 \
  --results-dir .local/results/orientdb/sf10_0
```

Use `--preflight-only` on this command before a timed run.

The formal runner discovers all 219 queries, including the 96 files under
`adapters/orientdb/queries/Pure_Join_Queries/`.

OrientDB plocal databases are exclusive-write resources. Never run a loader,
repair tool, console, or second worker against a database already opened by an
active benchmark. Formal Update execution uses bounded native batches,
explicit compensation, staging provenance, and baseline recovery checks.
