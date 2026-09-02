# Table Cardinalities

[`table-cardinalities.csv`](table-cardinalities.csv) records logical input rows
for the 30 SciSciNet CSVs at every GRBench scale factor. Headers are excluded.

## Provenance

- sf10_0 through sf10_3 use CSV-parser source counts recorded by a completed
  loader audit. Duplicate physical projections of one source CSV were required
  to agree before a count was accepted.
- sf10_4 uses Parquet footer row counts from the SciSciNet-v2 source. The
  derived `sciscinet_author_affiliation.csv` count comes from its deterministic
  projection.
- `PaperDetails` has one source record per retained `Papers` record at every
  scale.

These are source-table cardinalities, not necessarily DBMS-loaded graph-edge
counts. A graph loader may reject or explicitly project rows whose endpoint
vertices are absent. Such differences must be reported separately as loaded,
skipped, placeholder, and malformed-row counts; they must not overwrite this
source inventory.
