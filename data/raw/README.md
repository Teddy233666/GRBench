# Raw Data

This directory is the local landing area for externally obtained source data.
Large data files are ignored by Git; only this documentation is published.

Place the highest-scale SciSciNet-v2 Parquet snapshot under:

```text
data/raw/sciscinet-v2/
```

The conversion code expects Parquet files corresponding to the 30 canonical
CSV names in `data/schema/sciscinet.py`. `sciscinet_paperdetails`
may need to be obtained separately from the provider because of its size. See
`THIRD_PARTY_NOTICES.md` and `docs/data-preparation.md` before downloading.

Auxiliary IMDb or MOOCCube inputs used by historical generators belong under
`data/raw/IMDB/` and `data/raw/MOOCCube/`. They are not part of the canonical
SciSciNet benchmark.
