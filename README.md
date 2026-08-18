# GRBench

GRBench is a cross-model benchmark for relational, graph, and relational-graph
database systems. This repository publishes one canonical SciSciNet workload
and adapters for AgensGraph, ArangoDB, DuckDB, GrainDB, Kuzu, OrientDB, and
PostgreSQL.

This publication is a static release candidate. Repository checks pass, but
the reorganized adapters have not completed a fresh seven-system live oracle
run. Historical files under `results/latest-observed/` are published for
provenance and are not cross-system-comparable results. See
`docs/development/release-readiness.md` for the exact validation boundary.

Only Kuzu and OrientDB currently have maintained repository-relative runners.
The other adapters publish audited translations and historical implementation
evidence, not an end-to-end portable seven-system benchmark harness.

## Workload Contract

The canonical suite contains 123 queries:

- 96 main relational-graph and graph queries;
- 15 shortest-path queries;
- 12 Update queries named `1a.sql` through `6b.sql`.

`benchmark/queries/canonical/` is authoritative. Historical Update files with
a `c` suffix are retained only under `legacy/update-v0/`. `Pure_Join_Queries`
is a logical alias of the 96 main queries and is not executed as an additional
workload.

The `canonical_full_v1` data profile requires 30 CSV files. The files and
their logical projections are listed in `benchmark/manifests/data_profile.csv`.
Datasets and database files are not distributed in this repository.

## Repository Layout

- `benchmark/`: canonical queries, data schema, generation tools, manifests.
- `adapters/`: engine-specific queries, loaders, runners, and documentation.
- `results/`: curated observed results, comparability tiers, provenance hashes.
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

`results/latest-observed/` contains the newest retained artifact for each
available historical run. These files are not automatically cross-system
comparable; consult `results/manifests/published_results.csv` and
`docs/results/README.md`. `results/comparable/` accepts only artifacts that
pass the current benchmark contract.

Code and documentation are licensed under Apache-2.0 (`LICENSE`). Published
result tables are licensed under CC BY 4.0 (`RESULTS_LICENSE`). Dataset and
third-party DBMS licenses remain separate.
Dataset provenance and the release-owner authorization boundary are documented
in `THIRD_PARTY_NOTICES.md` and
`docs/development/provenance-and-licensing.md`.
