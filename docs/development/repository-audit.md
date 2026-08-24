# Repository Audit

## Source State

The release was assembled from three local source trees represented by the
aliases in `migration-map.md`. The independent publication candidate has an
unborn `main` branch, no Git objects, and no remote. It does not share Git
history or object storage with the source trees.

The source trees are retained privately for provenance. Publication must start
from this clean candidate; importing an inherited history would require a new
large-blob and sensitive-history audit.

## Findings

- Canonical main/shortest/Update coverage is 96/15/12.
- Pure Join is retained as a logical alias manifest, not duplicate files.
- The full data contract has 30 CSV inputs and 31 logical projections.
- Legacy loaders and shell runners contain workstation-specific paths; they
  remain explicitly non-portable until replaced.
- Selected historical results use different repetitions, headers, query
  revisions, or coverage and are therefore not cross-system comparable.
- No high-confidence credential or private-address match remains in the
  publication surface. Configuration examples contain blank secret values.
- Current worktree files pass the 10 MiB publication limit, but Git history
  still contains larger blobs.
- ArangoDB's 15 Shortest Path translations were re-audited; multiple unrelated
  or wrong-aggregate implementations were replaced with canonical mappings.
- Update's 16 directly referenced support tables now have one shared baseline
  derivation at `scripts/data_generation/derive_update_staging.sql`.

## Remaining Risk

Most adapters have static semantic review but no post-reorganization live
database run. Kuzu's three runners now share one warmup/three-run median
contract, but still require live full-profile and oracle validation; Update
`4a/4b` also retain a documented graph-integrity mismatch. OrientDB has a newer
formal run in progress and its incomplete result must not replace the retained
snapshot. Portable formal runners are still missing for AgensGraph, ArangoDB,
DuckDB, GrainDB, and PostgreSQL.

The clean candidate excludes the previously observed large legacy object pack.
Before the first push, a clean-clone simulation must confirm that normalization
does not invalidate query or result manifests.
