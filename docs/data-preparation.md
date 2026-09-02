# Data Preparation

## Source and Destination

GRBench does not distribute SciSciNet data. Place an externally obtained
SciSciNet-v2 Parquet snapshot under `data/raw/sciscinet-v2/`. The default
conversion destination is `data/processed/sf10_4/`; lower scale factors are
derived under `data/processed/sf10_3/` through `sf10_0/`.

The source, licensing, and citation notes are in `THIRD_PARTY_NOTICES.md`.
Set paths by copying `config/env.example` to an ignored `.env` file and sourcing
it from the repository root.

## Canonical Files

Each processed SF directory must contain these 30 files:

```text
hit_papers_level0.csv
hit_papers_level1.csv
normalized_citations_level0.csv
normalized_citations_level1.csv
sciscinet_affiliations.csv
sciscinet_affl_assoc_affl.csv
sciscinet_author_affiliation.csv
sciscinet_author_details.csv
sciscinet_authors.csv
sciscinet_authors_paperid.csv
sciscinet_clinicaltrials_metadata.csv
sciscinet_fields.csv
sciscinet_link_clinicaltrials.csv
sciscinet_link_newsfeed.csv
sciscinet_link_nih.csv
sciscinet_link_nobellaureates.csv
sciscinet_link_nsf.csv
sciscinet_link_patents.csv
sciscinet_link_twitter.csv
sciscinet_newsfeed_metadata.csv
sciscinet_nih_metadata.csv
sciscinet_nsf_metadata.csv
sciscinet_paper_author_affiliation.csv
sciscinet_paperdetails.csv
sciscinet_paperfields.csv
sciscinet_paperrefs.csv
sciscinet_papers.csv
sciscinet_papersources.csv
sciscinet_sources.csv
sciscinet_twitter_metadata.csv
```

`data/schema/sciscinet.py` is authoritative for logical names, source CSVs,
keys, and edge endpoints.

## Generate the Highest Scale

```sh
python3 -m venv .venv-data
.venv-data/bin/pip install -r requirements-data.txt
set -a; . ./.env; set +a
.venv-data/bin/python scripts/data_generation/sciscinet/csv_generator.py
```

The converter reads `SCISCINET_PARQUET_ROOT` and writes
`SCISCINET_CSV_ROOT`, which default to `data/raw/sciscinet-v2` and
`data/processed/sf10_4`.

## Derive Lower Scale Factors

```sh
.venv-data/bin/python scripts/data_generation/sciscinet/interface.py \
  --data-root data/processed --highest-scale 4
```

The command derives `sf10_3`, `sf10_2`, `sf10_1`, and `sf10_0` in descending
order using deterministic seed 42. It does not download or construct sf10_4.

Validate filenames without opening a database:

```sh
python3 scripts/data_generation/validate_data_profile.py \
  --data-root data/processed --sf sf10_0
```

Update support snapshots are derived after loading a healthy baseline. The
portable SQL definition is `scripts/data_generation/derive_update_staging.sql`;
engine-specific loaders may create an equivalent projection under
`.local/<engine>/staging/`.
