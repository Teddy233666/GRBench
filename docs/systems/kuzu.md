# Kuzu

Install the pinned Python bindings:

```sh
python3 -m venv .venv-kuzu
.venv-kuzu/bin/pip install -r adapters/kuzu/requirements.txt
```

Load one scale factor into the default ignored `.local/` area:

```sh
GRBENCH_DATA_ROOT=.local/data .venv-kuzu/bin/python adapters/kuzu/load.py \
  --dataset sf10_0 --threads 8 --strict-rel-copy
```

Smoke-check the required non-empty graph tables before benchmarking:

```sh
.venv-kuzu/bin/python adapters/kuzu/tools/validate_database.py \
  --db-path .local/kuzu/db/db_sf10_0
```

For a formal sf10_4 database, add `--count-profile sf10_4` to enforce the
published exact counts. The default smoke check is not a completeness proof;
formal runs must also retain loader source/loaded/skipped counts and input
hashes.

`run_main.py`, `run_shortest.py`, and `run_update.py` are the maintained
adapter entry points. Each defaults to one unmeasured warmup and three measured
runs, then publishes elapsed, CPU, and RSS from the median-elapsed run. RSS is
reported in MiB. Use a new result path or `--overwrite` when replacing older
single-run CSV files.

The shortest-path translation bounds SQL/PGQ unbounded paths with
`--max-unbounded-depth`; publish that value. Update defaults to a fresh working
database copy per repetition. Copy creation, staging, paired setup, validation,
cleanup, and rollback are outside the measurement window. The
`--transaction-rollback` mode is diagnostic and is not the formal isolation
mode.

Run the maintained suites from the repository root:

```sh
.venv-kuzu/bin/python adapters/kuzu/run_main.py \
  --dataset sf10_0 --results .local/results/kuzu_sf10_0_main.csv --overwrite
.venv-kuzu/bin/python adapters/kuzu/run_shortest.py \
  --dataset sf10_0 --results .local/results/kuzu_sf10_0_shortest.csv --overwrite
.venv-kuzu/bin/python adapters/kuzu/run_update.py \
  --dataset sf10_0 --results .local/results/kuzu_sf10_0_update.csv --overwrite
```

Update requires the untimed support CSVs under `.local/update-staging/`, derived
from the healthy loaded baseline as described in `docs/data/README.md`.

Kuzu's graph-integrity rules prevent Update `4a/4b` from exactly matching the
relational operation that deletes and restores only `Authors_Gender` rows while
leaving incident relationship tables untouched. Those two tasks remain
documented with that model limitation until an independently validated lossless
projection is implemented.
