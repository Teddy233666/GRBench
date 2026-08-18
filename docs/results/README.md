# Published Results

Result CSVs are stored directly under `results/<engine>/` for AgensGraph,
ArangoDB, DuckDB, GrainDB, Kuzu, OrientDB, and PostgreSQL. Source information,
notes, sizes, and SHA-256 values are recorded in
`results/manifests/published_results.csv`.

Public copies replace workstation-specific absolute paths with stable aliases.
This changes only path-valued CSV cells and serialization, not measured values.
`results/manifests/source_results.csv` preserves the original source size and
SHA-256; `published_results.csv` records both source and public-copy hashes.
Run `python3 tools/sanitize_result_paths.py` to verify that no known host path
remains.

Result tables are licensed under CC BY 4.0; cite GRBench and identify any
modifications.
