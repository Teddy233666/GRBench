# OrientDB Contract-v4 Five-SF Execution Plan

> Historical operations record. This plan predates the public 123-query
> contract and counted 96 Pure Join aliases as additional reads. It is retained
> only as provenance and must not be used as a release benchmark entry point.
> The timestamped oracle, readiness, recovery, and journal artifacts named below
> are not distributed. Their paths are provenance identifiers, not valid links
> in a public checkout.

Last updated: 2026-08-04 (Asia/Shanghai)

## Scope And Decisions

- Build and benchmark `sf10_0`, `sf10_1`, `sf10_2`, `sf10_3`, and `sf10_4`.
- Execute all 219 SQL files per SF: 207 reads and 12 Updates.
- Use `queries/orientdb_sciscinet_tasks_native_graph` and immutable source
  snapshot `queries/sciscinet_tasks_contract_v3_source`.
- Validate every read result against
  `results/duckdb_oracle_all_sf_contract_v3.json`; it contains 207 successful
  oracle entries for each of the five SFs.
- Reuse the existing Contract-v4 Update measurements for `sf10_0~sf10_2` and
  retain their original provenance and status. Do not relabel a timeout or a
  measurement-contract mismatch as successful.
- Run fresh Updates for rebuilt `sf10_3` and completed `sf10_4`.
- Keep Update `1a/1b/4a/4b` as OrientDB cascade extensions. Execute and report
  them, but exclude them from cross-engine aggregates.

## Confirmed Current State

- `sf10_0~sf10_2` passed the latest strict preflight:
  `results/readiness_v4/sf10_0_to_sf10_2_preformal_preflight_v4_20260802_211601`.
- `sf10_3` is not usable. Before the failed Update it had
  `PaperReferences=249,436,785`; it now has `216,376,785`, a loss of
  `33,060,000` edges. Recovery repeatedly fails on RID `#140:14040323` with
  `IllegalArgumentException: Change type is incorrect`. Evidence is under
  `results/readiness_v4/sf10_3_update1_crash_recovery_v4_20260728/`.
- No second usable OrientDB `sf10_3` copy exists. It must be rebuilt from
  `legacy_host_data/grbench/sf10_3`.
- `sf10_4` WAL recovery finished on 2026-08-03 at 00:08 and reached
  `GRBENCH_READY`, but it logged many magic-number failures in
  `paperreferences.cpm`. A post-recovery probe found
  `PaperReferences=584,450,000`, only 41 legacy manifest rows, no strict source
  fingerprints, and no `_MissingEndpoint` class. The approximately 798 GiB
  database is physically damaged and provenance-incomplete; prefix resume is
  rejected and `sf10_4` must be rebuilt.
- Post-recovery sf10_4 evidence is under
  `results/readiness_v4/sf10_4_post_wal_probe_20260804_101548` and the journal
  for `orientdb-sf10-4-wal-recovery-20260802.service`.
- `/data` had approximately 954 GiB free on 2026-08-04. Rebuilding `sf10_3` in place is
  destructive but releases its approximately 686 GiB broken directory before
  recreating it. Preserve evidence first; do not attempt a second full copy on
  the same filesystem without rechecking capacity.

## Non-Negotiable Safety Rules

- Run at most one OrientDB loader, recovery worker, or benchmark worker at a
  time. Never open the same plocal database from two processes.
- Let WAL recovery finish naturally. A forced stop creates another unclean
  shutdown and restarts the recovery cost.
- Treat manifest `DONE` as valid only when source fingerprints match and
  `source_rows == loaded_rows` with `skipped_rows == 0`.
- Use `--orphan-edge-mode placeholder`; do not silently discard an edge whose
  typed endpoint is absent.
- Use per-SF `--update-source-mode derived`; never use the shared legacy
  DuckDB Update CSV staging for a formal database.
- Use a fresh result directory for every preflight or benchmark attempt.
- Never convert `TIMEOUT`, `CRASHED`, failed validation, or missing oracle to
  `OK`.

## Step 1: Preserve Evidence And Rebuild sf10_3

Before rebuilding, preserve the existing recovery logs, service status,
database size, file inventory, current class-count evidence, and the exact
loader/query revisions in a timestamped directory under `results/readiness_v4`.
Do not copy the 686 GiB broken database itself.

The following rebuild is deliberately destructive: `--rebuild` removes
`legacy_host_data/grbench/orientdb_manual_data_loaded/sf10_3` before creating a clean
database from `legacy_host_data/grbench/sf10_3`.

```sh
cd legacy_orientdb
python3 load_orientdb_data.py \
  --sf sf10_3 \
  --data-root legacy_host_data/grbench \
  --db-dir legacy_host_data/grbench/orientdb_manual_data_loaded \
  --query-root queries/orientdb_sciscinet_tasks_native_graph \
  --heap 96g --direct-memory 80g --disk-cache-mb 65536 \
  --batch-size 50000 --skip-final-counts \
  --orphan-edge-mode placeholder --update-source-mode derived \
  --rebuild
```

`legacy_host_data/grbench/sf10_3/hit_papers_level1.csv` already points to
`hit_papers_level1_export.csv`. The normal full load derives all 17 Update
staging classes after loading and indexing the base data.

## Step 2: Validate And Benchmark sf10_0 Through sf10_3

Run the static audit and strict preflight for `sf10_0~sf10_3`. If all pass,
run their formal reads and the Update result set before starting the much longer
sf10_4 rebuild. Do not overlap benchmark execution with any loader.

While sf10_3 is rebuilding, the database-free input audit may run safely:

```sh
cd legacy_orientdb
stamp="$(date '+%Y%m%d_%H%M%S')"
python3 audit_orientdb_formal_inputs.py \
  --output "results/readiness_v4/formal_input_audit_${stamp}.json"
```

After the rebuild finishes, use the guarded serial phase script. It refuses to
start while any OrientDB loader, recovery, or benchmark process is active:

```sh
cd legacy_orientdb
scripts/run_sf10_0_to_sf10_3_formal_after_rebuild.sh
```

## Step 3: Preserve Evidence And Rebuild sf10_4

Preserve the post-WAL probe and complete recovery journal, then delete the
damaged database only when no OrientDB process is active. The following command
is a full rebuild; prefix resume and skipped-edge repair are not permitted for
this copy:

```sh
cd legacy_orientdb
python3 load_orientdb_data.py \
  --sf sf10_4 \
  --data-root legacy_host_data/grbench/orientdb_inputs \
  --db-dir legacy_host_data/grbench/orientdb_manual_data_loaded \
  --query-root queries/orientdb_sciscinet_tasks_native_graph \
  --heap 96g --direct-memory 80g --disk-cache-mb 65536 \
  --batch-size 50000 --skip-final-counts \
  --orphan-edge-mode placeholder --update-source-mode derived \
  --rebuild
```

Run the rebuild as an independent systemd service and preserve its journal.
Recheck `/data` capacity before deleting the old sf10_4 directory and during
the load.

## Step 4: Static Audit And Five Independent Preflights

```sh
cd legacy_orientdb
python3 -m py_compile run_orientdb.py load_orientdb_data.py audit_benchmark_contract.py
python3 audit_benchmark_contract.py

stamp="$(date '+%Y%m%d_%H%M%S')"
python3 run_orientdb.py \
  --sf sf10_0 --sf sf10_1 --sf sf10_2 --sf sf10_3 --sf sf10_4 \
  --query-root queries/orientdb_sciscinet_tasks_native_graph \
  --source-query-root queries/sciscinet_tasks_contract_v3_source \
  --db-dir legacy_host_data/grbench/orientdb_manual_data_loaded \
  --load-mode orientdb_manual_data_loaded_native_graph \
  --expected-results results/duckdb_oracle_all_sf_contract_v3.json \
  --execution-mode warm --heap '-Xms4g -Xmx64g' \
  --timeout 18000 --update-setup-timeout 18000 \
  --update-recovery-timeout 18000 --update-recovery-max-attempts 12 \
  --preflight-only \
  --results-dir "results/readiness_v4/all_sf_preformal_${stamp}"
```

Require all five preflights to pass. A failure in one SF blocks only that SF;
it must not be hidden by successful preflights from the others.

## Step 5: Formal Read Benchmark

Reads use one persistent worker per SF, one unmeasured warmup, three measured
runs, median elapsed time, and 0.01 second resource sampling. Run SFs serially.

```sh
stamp="$(date '+%Y%m%d_%H%M%S')"
python3 run_orientdb.py \
  --sf sf10_0 --sf sf10_1 --sf sf10_2 --sf sf10_3 --sf sf10_4 \
  --stop-before-update \
  --query-root queries/orientdb_sciscinet_tasks_native_graph \
  --source-query-root queries/sciscinet_tasks_contract_v3_source \
  --db-dir legacy_host_data/grbench/orientdb_manual_data_loaded \
  --load-mode orientdb_manual_data_loaded_native_graph \
  --expected-results results/duckdb_oracle_all_sf_contract_v3.json \
  --execution-mode warm --runs 3 --warmup-runs 1 \
  --timeout 18000 --resource-sample-interval 0.01 \
  --worker-max-result-rows 10000 --heap '-Xms4g -Xmx64g' \
  --results-dir "results/formal_contract_v4_reads_all_sf_${stamp}"
```

Expected total: 1,035 rows. Every row must be `OK`, match the DuckDB row count
and canonical value hash, and have `comparison_eligible=true`.

## Step 6: Formal Update Result Set

The reusable `sf10_0~sf10_2` measurements were collected with one measured
run, no warmup, 10,000-row native batches, and 0.01 second sampling. Therefore
the Update result set uses that same measurement contract for fresh `sf10_3`
and `sf10_4` rows. Combining these reused rows with a `runs=3/warmup=1`
invocation would correctly mark them as measurement-contract failures.

```sh
stamp="$(date '+%Y%m%d_%H%M%S')"
python3 run_orientdb.py \
  --sf sf10_0 --sf sf10_1 --sf sf10_2 --sf sf10_3 --sf sf10_4 \
  --category update \
  --query-root queries/orientdb_sciscinet_tasks_native_graph \
  --source-query-root queries/sciscinet_tasks_contract_v3_source \
  --db-dir legacy_host_data/grbench/orientdb_manual_data_loaded \
  --load-mode orientdb_manual_data_loaded_native_graph \
  --execution-mode warm --runs 1 --warmup-runs 0 \
  --timeout 18000 --update-setup-timeout 18000 \
  --update-recovery-timeout 18000 --update-recovery-max-attempts 12 \
  --update-batch-size 10000 --resource-sample-interval 0.01 \
  --heap '-Xms4g -Xmx64g' \
  --reuse-update-results results/readiness_v4/sf10_0_full_update_acceptance_v4_20260723 \
  --reuse-update-results results/readiness_v4/sf10_1_full_update_acceptance_v4_20260723 \
  --reuse-update-results results/readiness_v4/sf10_2_update1_regression_v4_20260722 \
  --reuse-update-results results/readiness_v4/sf10_2_update_2_to_6_acceptance_v4_20260723 \
  --results-dir "results/formal_contract_v4_updates_all_sf_${stamp}"
```

Expected total: 60 rows. The two reused sf10_2 rows `1a.sql` and `3a.sql`
remain `TIMEOUT`; their successful emergency recovery proves the database was
restored, not that the timed queries succeeded. They remain in the result set
with `comparison_eligible=false`. The 20 fresh sf10_3/sf10_4 Update rows must
pass validation and baseline restoration. OrientDB cascade-extension rows are
reported but remain cross-engine ineligible by design.

## Step 7: Merge, Audit, And Archive

- Produce a new combined artifact; do not overwrite the read or Update source
  result directories.
- Require exactly 1,095 unique `(sf, sql_file)` rows: 1,035 reads and 60
  Updates.
- Preserve `result_origin`, reuse source path and SHA-256, original run/warmup
  counts, loader mode, every class's `source_rows/loaded_rows/skipped_rows`,
  database preflight, and all worker logs.
- Keep workload-specific measurement contracts explicit. Cross-engine read
  comparisons require `runs=3/warmup=1`; cross-engine Update comparisons
  require `runs=1/warmup=0` and the same batch/timing window.
- Run `python3 audit_benchmark_contract.py` again and archive its output.
- Do not publish a failed or ineligible row in an aggregate latency ranking.

## Failure Policy

- If a worker startup is recovering WAL, wait up to the configured 18,000
  seconds; do not kill it at the old 1,800 second limit.
- If Update recovery or preflight cannot prove the exact baseline, mark the SF
  unusable and stop all later work on that SF.
- If sf10_4 prefix assumptions fail, rebuild or obtain a known-good copy rather
  than appending to an unverified edge class.
- If disk free space approaches the loader's remaining-growth estimate plus a
  safety reserve, stop before ENOSPC causes another unclean database.
