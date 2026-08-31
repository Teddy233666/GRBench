# Kuzu Runners

`run_main.py`, `run_shortest.py`, and `run_update.py` are maintained formal
entry points. `measurement.py` implements the shared warmup/repetition and
median-elapsed-run selection contract.

`run_shortest.py` loads the query inventory and Cypher templates from
`../queries/Shortest_Path_Queries/`; query semantics are not embedded in the
runner.
