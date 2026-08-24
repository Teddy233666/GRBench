# Data Documentation

The complete preparation workflow is documented in
[`docs/data-preparation.md`](../data-preparation.md).

Key paths:

- external Parquet input: `data/raw/sciscinet-v2/`;
- canonical CSV output: `data/processed/sf10_0/` through `sf10_4/`;
- schema contract: `data/schema/sciscinet.py`;
- 30-file manifest: `benchmark/manifests/data_profile.csv`;
- conversion and SF extraction: `scripts/data_generation/sciscinet/`;
- Update support derivation: `scripts/data_generation/derive_update_staging.sql`;
- engine-local staging: `.local/<engine>/staging/`.

Raw and processed data files are ignored by Git. Every loader must record or
otherwise verify source rows, loaded rows, skipped rows, dangling endpoints,
and source hashes before its database can be treated as healthy.
