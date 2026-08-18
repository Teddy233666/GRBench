# Published Results

Results are divided by evidence level:

- `latest-observed/`: newest retained measurements, including pre-contract
  files and runs made before later query corrections.
- `comparable/`: only current-contract, oracle-validated measurements.
- `legacy/`: superseded or diagnostic artifacts retained for provenance.

The current release publishes historical observations for all seven engines,
but no artifact is yet promoted to `comparable`. Reasons and SHA-256 values are
in `results/manifests/published_results.csv`. In particular, legacy files may
use old queries, single runs, duplicate Pure Join coverage, inconsistent
headers, or incomplete scale-factor coverage.

Public copies replace workstation-specific absolute paths with stable aliases.
This changes only path-valued CSV cells and serialization, not measured values.
`results/manifests/source_results.csv` preserves the original source size and
SHA-256; `published_results.csv` records both source and public-copy hashes.
Run `python3 tools/sanitize_result_paths.py` to verify that no known host path
remains.

Do not combine files solely because their columns have the same name. Verify
query revision, data profile, warmup/repeat count, timeout, process-tree
sampling, metric units, and Update isolation. Result tables are licensed under
CC BY 4.0; cite GRBench and identify any modifications.
