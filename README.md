# GRBench

GRBench is a cross-model benchmark for relational, graph, and relational-graph
database systems. This repository publishes one canonical SciSciNet workload
and adapters for AgensGraph, ArangoDB, DuckDB, GrainDB, Kuzu, OrientDB, and
PostgreSQL.

## Workload Contract

The canonical suite contains 123 queries:

- 96 main relational-graph and graph queries;
- 15 shortest-path queries;
- 12 Update queries named `1a.sql` through `6b.sql`.

`benchmark/queries/canonical/` is authoritative. Historical Update files with
a `c` suffix are retained only under `legacy/update-v0/`. `Pure_Join_Queries`
contains pure relational implementations of the 96 main queries.

The `canonical_full_v1` data profile requires 30 CSV files. The files and
their logical projections are listed in `benchmark/manifests/data_profile.csv`.
Datasets and database files are not distributed in this repository.

## Repository Layout

- `benchmark/`: canonical queries, data schema, generation tools, manifests.
- `adapters/`: engine-specific queries, loaders, runners, and documentation.
- `results/`: result CSVs organized by database system, plus provenance hashes.
- `docs/`: benchmark contract, data preparation, systems, and development notes.
- `tools/`: deterministic manifest generation and repository validation.
- `legacy/`: superseded workload artifacts kept for provenance only.

## Validate a Checkout

Python 3.10 or newer is required for repository checks.

```sh
python3 -m pip install -r requirements-dev.txt
python3 tools/generate_manifests.py
python3 tools/audit_query_semantics.py
python3 tools/validate_repository.py --strict-paths
```

Formal measurements use one warmup and three measured executions. The row
whose elapsed time is the median supplies every reported metric for that
query. Update setup, validation, compensation, and rollback are excluded from
elapsed time. See `docs/benchmark-contract.md` before publishing results.

Engine setup and commands are documented under `docs/systems/`. Local paths
and credentials belong in environment variables; start with `config/env.example`.
Contribution requirements are documented in `CONTRIBUTING.md`.

## Results and Licensing

Result CSVs are organized by database system under `results/<engine>/`.
Provenance metadata and SHA-256 values are recorded in
`results/manifests/published_results.csv`; see `docs/results/README.md`.

Code and documentation are licensed under Apache-2.0 (`LICENSE`). Published
result tables are licensed under CC BY 4.0 (`RESULTS_LICENSE`). Dataset and
third-party DBMS licenses remain separate.
Dataset provenance and the release-owner authorization boundary are documented
in `THIRD_PARTY_NOTICES.md` and
`docs/development/provenance-and-licensing.md`.
