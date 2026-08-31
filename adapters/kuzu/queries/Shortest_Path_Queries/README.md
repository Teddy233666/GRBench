# Kuzu Shortest Path Queries

The 15 primary `1a.cypher` through `5c.cypher` files contain the Kuzu
translations of the canonical SQL/PGQ shortest-path workload. Kuzu 0.11.3
does not directly support `ANY SHORTEST`, so `run_shortest.py` executes one
exact-depth query per permitted path length and aggregates the endpoint
minimum.

`manifest.json` records benchmark order, result metadata, and depth bounds.
The runner replaces `{{DEPTH_RANGE}}` with an exact Kuzu relationship range;
for depth one it removes the token. Queries whose range includes zero use the
corresponding `*.zero.cypher` file for that step.

Run these templates through `adapters/kuzu/runners/run_shortest.py`; files
containing `{{DEPTH_RANGE}}` are not standalone Cypher statements until
rendered by the runner.
