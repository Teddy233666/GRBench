# Processed Scale Factors

Generated SciSciNet CSV scale factors use this layout:

```text
data/processed/
  sf10_0/
  sf10_1/
  sf10_2/
  sf10_3/
  sf10_4/
```

Every `sf10_N` directory must contain the same 30 filenames defined in
`data/schema/sciscinet.py`. Generated CSV files are ignored by Git;
this README is the only tracked file in this directory.

Database-specific projections that are not lossless canonical inputs must stay
under `.local/<engine>/staging/`, not beside the canonical SF directories.
