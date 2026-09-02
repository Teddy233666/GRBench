# Kuzu Update Queries

The 12 `U1a.cypher` through `U6b.cypher` files contain the measured Kuzu
statements for the paper's U-series workload. `manifest.json` defines benchmark
order, result labels, and the unmeasured setup query required by each restore
task.

The paper groups templates by operation type: U1-U2 update vertices only,
U3-U4 update edges, and U5-U6 update vertices with incident edges. Suffix `a`
is deletion and suffix `b` restores the same records.

Files may contain multiple statements. Each statement starts with an exact
`-- statement` marker so the loader does not need to parse Cypher semicolons.
Upper-case `{{NAME}}` tokens are staging CSV paths rendered by
`benchmark/kuzu/runners/update_query_loader.py` before execution.

Database copies, staging-table creation, setup timing boundaries, validation,
and cleanup remain runner responsibilities. Run these files through
`benchmark/kuzu/runners/run_update.py`; templates containing path tokens are not
standalone statements until rendered.
