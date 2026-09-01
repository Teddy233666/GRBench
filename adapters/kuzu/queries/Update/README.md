# Kuzu Update Queries

The 12 `1a.cypher` through `6b.cypher` files contain the measured Kuzu
statements for the canonical Update workload. `manifest.json` defines benchmark
order, result labels, and the unmeasured setup query required by each restore
task.

Files may contain multiple statements. Each statement starts with an exact
`-- statement` marker so the loader does not need to parse Cypher semicolons.
Upper-case `{{NAME}}` tokens are staging CSV paths rendered by
`adapters/kuzu/runners/update_query_loader.py` before execution.

Database copies, staging-table creation, setup timing boundaries, validation,
and cleanup remain runner responsibilities. Run these files through
`adapters/kuzu/runners/run_update.py`; templates containing path tokens are not
standalone statements until rendered.
