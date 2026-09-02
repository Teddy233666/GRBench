# Contributing to GRBench

Use an issue or pull request to identify the affected database, query suite,
and scale factor. Keep database-specific code under
`benchmark/<database>/{loaders,queries,runners}` and shared data preparation
code under `data/` or `scripts/data_generation/`.

Before opening a pull request, run the checks defined in
`.github/workflows/validate.yml`. At minimum, compile Python files, check every
shell script with `bash -n`, and check ArangoDB JavaScript with `node --check`.
PostgreSQL runner changes must preserve the output of each `--list` command.

Query changes must preserve the task ID and update every affected database
translation. Describe anchors, predicates, edge direction, optional-join
behavior, output aliases, and Update state changes. Parser or execution success
alone is not semantic equivalence; include result-oracle or state-oracle
evidence when making that claim.

Do not commit datasets, database state, credentials, private addresses,
machine-specific paths, logs, caches, or benchmark outputs. Store local
artifacts under `.local/`, `data/raw/`, or `data/processed/` as appropriate.

Use short imperative commit subjects such as `fix arangodb optional joins`.
Pull requests should list the DBMS versions and validation commands used.
