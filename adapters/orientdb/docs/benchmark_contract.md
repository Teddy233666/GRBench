# GRBench Cross-Engine Benchmark Contract

Contract version: `grbench-cross-engine-v4-2026-07-20`

## Valid Result Definition

An execution status of `OK` only means that the engine completed the SQL. A row
is valid for cross-engine comparison only when `comparison_eligible=true`.
That requires all of the following:

1. The query file belongs to the audited query revision.
2. Every referenced class has a `DONE` loader manifest row with
   `source_rows == loaded_rows` and `skipped_rows == 0`.
3. The loader manifest's source CSV and configuration fingerprints match the
   current inputs, and the source row count was verified.
4. The fully consumed, canonically normalized result matches an external
   expected-result SHA-256 and row count.
5. The timing, timeout, repeat count, cache policy, and resource sampling
   settings match across every engine.
6. An Update task passes setup, native batch accounting, postcondition,
   explicit compensation, support-state, and baseline recovery checks.

Historical result files produced before this contract do not satisfy these
requirements and must not be merged with contract-v4 results. In particular,
contract-v3's single-transaction Update execution can retain millions of
deleted record versions and is not valid for the formal large-SF workload.

## Timing And Resources

- Use one already-started engine session per scale factor.
- Measure from the worker execution boundary until the complete result has been
  consumed; client request/response time is recorded separately.
- Do not include database startup, Update setup, validation, normal
  compensation, emergency recovery, result hashing, or report writing in the
  measured interval.
- Use the same timeout for the measured phase on every engine.
- Use the same number of runs and select the median elapsed run. CPU and RSS
  metrics must come from that same run, not from an average across different
  runs.
- Sample the complete engine process tree every `0.01` seconds. CPU percent may
  exceed 100 on multi-core systems. Memory is summed resident set size in MiB.
- Force the legacy OrientDB console to a `COLUMNS`/`maxWidth` value of `16384`.
  Terminal-width truncation changes displayed values and invalidates result
  hashes.

The current shell-based DuckDB and PostgreSQL scripts and the historical Kuzu
Update runner do not all satisfy this timing contract. Their old CSV files are
reference artifacts, not directly comparable results.

## Read Queries

The worker consumes and fully materializes OrientDB result sets, trims scalar
text, sorts unordered rows, and hashes the normalized column/row structure.
An expected-results JSON manifest is required before a read query can become
comparison eligible. The legacy cold-console path still removes its marker
result, but it is not the strict data-loaded path.

The static audit command is:

```sh
python3 adapters/orientdb/tools/audit_benchmark_contract.py
```

Validate a loaded database without executing timed queries:

```sh
python3 adapters/orientdb/runners/run_orientdb.py \
  --sf sf10_0 \
  --query-root adapters/orientdb/queries \
  --source-query-root benchmark/queries/canonical \
  --db-dir "${GRBENCH_ORIENTDB_DB_ROOT}" \
  --load-mode orientdb_manual_data_loaded_native_graph \
  --expected-results "${GRBENCH_ORIENTDB_ORACLE}" \
  --preflight-only \
  --results-dir results/preflight_sf10_0
```

The command returns nonzero for an invalid oracle, source fingerprint,
manifest count, dependency, or database class count. A normal strict run also
returns nonzero when any required query is missing or not comparison eligible.

The release uses `benchmark/queries/canonical` as its immutable source-query
snapshot. `docs/development/query-audit.md` records the approved upstream
corrections required to make the workload executable. Oracle and runner provenance must
use this same snapshot; mixing it with the uncorrected upstream directory is a
hard query-suite mismatch.

It checks all 123 executable adapter queries, the 96 logical Pure Join aliases,
known bad join patterns, optional-branch rewrites, and required Update SQL
mappings. Pure Join is represented only by
`benchmark/manifests/pure_join_aliases.csv`; duplicate physical query files are
not executed.

Generate a DuckDB result oracle in a pinned environment. The generator executes
the 123 canonical queries. It opens the reference data files read-only and
registers their property-graph metadata in an in-memory catalog:

```sh
python3 -m venv .venv-duckpgq-oracle
.venv-duckpgq-oracle/bin/pip install -r requirements-oracle.txt
.venv-duckpgq-oracle/bin/python generate_duckdb_oracle.py \
  --sf sf10_0 \
  --threads 8 \
  --output results/duckdb_oracle_sf10_0_contract_v3.json
```

DuckDB `1.2.2` is pinned because the available DuckPGQ extension is built for
that engine ABI. Loading it into DuckDB `1.5.1` caused a native crash during
the audit. The oracle records its format, selected query paths, source
query-suite SHA-256, and one source SQL SHA-256 per result. The OrientDB runner
rejects an old format, a mismatched query suite, or an alias entry before a
data-loaded benchmark starts.

## Update Queries

Each measured run uses this sequence:

1. Require per-SF staging with `loader_mode=derived_update_snapshot_v1`.
2. Read affected-class baseline counts and require exact agreement with the
   loader manifest.
3. Require nonempty per-SF staging with verified
   `derived_update_snapshot_v1` provenance. The loader creates these rows by
   executing the target predicate against that same loaded baseline.
4. Require every engine-owned Update support class to be empty.
5. For a `b` query, execute its paired `a` query as unmeasured setup through
   the native worker's bounded batch protocol.
6. Require the setup's modified-row, visited-row, missing-row, and committed
   batch counters to match the exact staging cardinalities, then validate the
   setup state.
7. Measure one `GRBENCH_UPDATE ... STRICT` request. The measured window covers
   every bounded transaction and commit needed to complete that logical
   Update, but excludes setup and validation.
8. Validate exact affected-class deltas. Classes which the source SQL leaves
   unchanged are also counted explicitly.
9. After a measured `a`, execute the paired `b` as unmeasured compensation.
   A measured `b` already ends in the baseline state.
10. Re-read affected-class and support-class counts and require exact baseline
    recovery.

If setup fails or times out, the measured query is not run and receives
`DEPENDENCY_FAILED`. Any partial batch failure invokes idempotent `RECOVER`,
which first normalizes the delete state and then restores the complete staging
snapshot. If recovery cannot prove the baseline, the result is
`BASELINE_CORRUPTED` and the scale-factor run stops.

The isolation label is
`batched_commits_with_explicit_compensation_and_verified_baseline_v1`. A
single outer transaction is forbidden: it retained every deleted record
version until rollback and caused the earlier `sf10_2/1a` 64GB OOM. The
default batch size is 10,000 records and is recorded in both metadata and each
Update result row.

OrientDB executes `1a/1b/4a/4b` as complete native-graph cascade extensions.
The delete statements remove every incident benchmark edge before deleting the
target vertices, and the restore statements recreate both vertices and edges
from per-SF derived staging. These tasks are marked
`ORIENTDB_CASCADE_EXTENSION`: they are executed and validated in full formal
runs, but remain ineligible for cross-engine aggregation because the unchanged
relational workloads delete only entity-table rows.

The strict native-graph Update comparison set contains `2a/2b`, `3a/3b`,
`5a/5b`, and `6a/6b`. These rows use
`correctness_status=PASS_UPDATE_STATE_TRANSITION`; an Update statement's scalar
console output is not treated as a result oracle.

Update 6 needs one OrientDB-specific representation step to preserve the
unchanged source-table semantics. Deleting an `Authors_Gender` vertex normally
cascades to `Authors_Paper`, although the source SQL deletes only
`Papers_to_Authors`, `affiliated_with`, and `Authors_Gender`. The worker moves
the selected authors to the indexed, non-subclass
`_GrbenchUpdate6AuthorShadow` during the delete state and moves them back
during restore. This keeps `Authors_Paper` rows and edges intact while making
the authors invisible to `Authors_Gender` queries. Preflight and every Update
6 iteration require the shadow class to be empty at baseline and verify its
exact staging count in the delete state.

Use the default query selection for complete formal runs. It executes all 12
Update files while `comparison_eligible` keeps the four OrientDB cascade
extensions out of cross-engine aggregation. Use `--strict-comparable-only`
only when a run intentionally needs the eight contract-aligned Update files.

## Loader Completeness

Strict imports use `--orphan-edge-mode placeholder` and must not use
`--skip-source-count`. If an edge endpoint is
missing from its vertex CSV, the loader connects that edge to a vertex in the
separate `_MissingEndpoint` class instead of dropping the source row. This
preserves edge cardinality while preventing a typed MATCH to `Papers`,
`Authors_Gender`, or another expected endpoint class from producing a false
match. `_LoadManifest` records `placeholder_rows` and requires
`source_rows == loaded_rows` with `skipped_rows == 0`. `_LoadManifest` also
records the source CSV path, source CSV SHA-256, whether the source row count
was actually scanned, and the loader configuration SHA-256. At Benchmark
startup the runner re-hashes the current CSV files and compares those
fingerprints with the database manifest. A legacy manifest without these
fields is not comparable.

Placeholders are unique by `(target_class, target_key, target_value)`. Update
restore scripts resolve either the normal typed endpoint or that unique
placeholder, so an orphan edge deleted during setup is restored without making
it visible to typed graph matches.

Existing clean databases can be audited and repaired without rebuilding valid
edge rows:

```sh
python3 repair_orientdb_orphan_edges.py --sf sf10_2 --sf sf10_3
python3 repair_orientdb_orphan_edges.py --sf sf10_2 --sf sf10_3 --execute
```

The first command is a dry run. The repair scans source edge CSVs and inserts
only rows whose endpoints need placeholders. A database whose current class
counts differ from `_LoadManifest` is contaminated and must be rebuilt instead
of repaired.

Formal Update staging must not come from the shared
`legacy DuckDB staging export` directory. Those files are one inconsistent
snapshot and do not represent every SF. The loader defaults to
`--update-source-mode derived` and derives all 17 staging classes from each
database's loaded baseline. Replace legacy staging in an otherwise clean
database with:

```sh
python3 adapters/orientdb/loaders/load_orientdb_data.py \
  --sf sf10_2 \
  --db-dir "${GRBENCH_ORIENTDB_DB_ROOT}" \
  --query-root adapters/orientdb/queries \
  --update-source-mode derived \
  --derive-updates-only \
  --skip-final-counts
```

`UPDATE_INPUT_INVALID` is a hard provenance failure and cannot be converted to
`OK` by `--resume`.

## Required Invocation

Use a new results directory and a v2 expected-results manifest generated by an
independent reference implementation:

```sh
python3 adapters/orientdb/runners/run_orientdb.py \
  --query-root adapters/orientdb/queries \
  --source-query-root benchmark/queries/canonical \
  --db-dir "${GRBENCH_ORIENTDB_DB_ROOT}" \
  --load-mode orientdb_manual_data_loaded_native_graph \
  --execution-mode warm \
  --runs 3 \
  --update-batch-size 10000 \
  --resource-sample-interval 0.01 \
  --expected-results /path/to/expected_results.json \
  --results-dir /path/to/new_contract_v4_results
```

Do not use `--resume` with a historical result directory. Contract-v4 resume
only skips rows that were already fully comparison eligible.
