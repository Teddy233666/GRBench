# Contributing to GRBench

Use an issue or pull request to describe the affected workload, adapter, or
result contract. Keep engine-specific syntax under `adapters/<engine>/` and
shared workload semantics under `benchmark/`.

Before opening a pull request, run:

```sh
python3 -m pip install -r requirements-dev.txt
python3 tools/generate_manifests.py
python3 tools/audit_query_semantics.py
python3 tools/validate_repository.py --strict-paths
```

Query changes must preserve the canonical query ID and update all affected
adapter translations and manifest hashes. Describe anchors, predicates, edge
direction, optional-join behavior, output aliases, and Update state changes in
the pull request. Execution success is not enough; include complete result or
state-oracle evidence when claiming semantic equivalence.

Do not commit datasets, database state, credentials, private addresses, local
paths, logs, caches, or unreviewed benchmark outputs. New result artifacts must
include provenance and hashes in `results/manifests/published_results.csv`.
Document compliance with `docs/benchmark-contract.md` in the result manifest.

Use short imperative commit subjects, such as `fix arangodb optional joins`.
List the validation commands and DBMS versions used in every pull request.
