# SciSciNet Data

GRBench does not redistribute datasets. Place each scale factor under:

```text
${GRBENCH_DATA_ROOT}/
  sf10_0/
  sf10_1/
  sf10_2/
  sf10_3/
  sf10_4/
```

The processing code targets SciSciNet-v2 from
https://github.com/Northwestern-CSSI/sciscinet. Cite the SciSciNet data paper
(https://doi.org/10.1038/s41597-023-02198-9) and verify the license of the exact
downloaded artifact. The provider's repository-level license and README license
reference currently disagree; see `THIRD_PARTY_NOTICES.md`.

Each directory must contain the 30 inputs listed in
`benchmark/manifests/data_profile.csv`. `PaperDetails` and `Twitter_Metadata`
are included even when a particular read workload does not reference them:
the full profile keeps loading/storage cost and future Update behavior
consistent across engines.

`benchmark/schema/sciscinet.py` defines logical vertices, edges, plain tables,
renames, keys, and endpoints. One CSV may project to multiple logical objects;
for example, `sciscinet_authors_paperid.csv` represents both edge directions.
Loaders must record source/loaded/skipped row counts and input hashes. Never
silently discard malformed rows or dangling endpoints.

The historical generator under `benchmark/data-generation/` requires
`requirements-data.txt` and environment paths from `config/env.example`.
Generated scale factors must be profiled before benchmark use; generation is
not a substitute for the loader health manifest.

Convert a separately obtained SciSciNet-v2 Parquet snapshot and derive lower
scale factors from the highest available CSV scale with:

```sh
python3 -m venv .venv-data
.venv-data/bin/pip install -r requirements-data.txt
SCISCINET_PARQUET_ROOT=.local/sciscinet-v2 \
SCISCINET_CSV_ROOT=.local/sciscinet-csv \
GRBENCH_DATA_ROOT=.local/data \
  .venv-data/bin/python benchmark/data-generation/processor/csv_generator.py
GRBENCH_DATA_ROOT=.local/data \
  .venv-data/bin/python benchmark/data-generation/processor/interface.py \
  --data-root .local/data --highest-scale 4
```

The scaling command expects `sf10_4` to exist and derives `sf10_3` down to
`sf10_0`; it does not download or create the highest-scale source snapshot.

Before Update measurements, derive all support snapshots from the loaded
baseline with `benchmark/setup/derive_update_staging.sql` or an audited
engine-equivalent loader step. Record row counts and hashes for each staging
object. Do not reuse another engine's staging export as formal input.
