# Benchmark Contract

## Canonical Workload

`benchmark/queries/canonical/` defines 96 main queries, 15 shortest-path
queries, and 12 Update queries. `query_manifest.csv` binds every file to a
stable query ID and SHA-256. Engine rewrites may change syntax and physical
schema mapping, but must preserve anchors, predicates, path direction,
optional/inner semantics, aggregation, and output columns.

Pure Join files are alternate relational implementations of the same 96
logical main queries. They are recorded as aliases and are not a second
performance workload. Update files with a `c` suffix are legacy artifacts.

## Data Contract

Formal runs use `canonical_full_v1`: all 30 CSV files in
`benchmark/manifests/data_profile.csv` are loaded or represented by a
documented lossless engine projection. Missing endpoints may be skipped only
when a row-level audit proves that the input references no canonical vertex;
the expected loaded count and exclusion reason must be published.

## Execution Contract

- Start one engine session per scale factor and record engine/config versions.
- Run one unmeasured warmup followed by three measured executions per query.
- Fully consume results inside the elapsed-time boundary.
- Select the measured run with median elapsed time. CPU and RSS come from that
  same run; never compute each output column's median independently.
- Sample the complete engine process tree every 10 ms by default. Report raw
  process CPU percent and resident set size in MiB.
- Apply the same per-query timeout to all engines and retain errors/timeouts.

For Update `b` queries, run the paired `a` query as unmeasured setup. For an
Update `a` measurement, run paired `b` as unmeasured compensation. Setup,
postcondition checks, compensation, emergency recovery, and rollback are not
part of elapsed time. Every repetition must begin and end at a verified
baseline; use an isolated physical copy when rollback cannot guarantee that.

The relational support tables referenced by Update are immutable snapshots
derived from the healthy baseline. `scripts/data_generation/derive_update_staging.sql`
defines the portable SQL derivation; engine-specific loaders may implement an
equivalent physical projection. Staging derivation is never a timed query.

## Correctness and Comparability

`OK` means execution completed, not that the result is correct. Result metadata
must record whether query/data hashes match, output rows or Update state
transitions pass an independent oracle, all required classes are healthy, and
measurement settings match this contract.
