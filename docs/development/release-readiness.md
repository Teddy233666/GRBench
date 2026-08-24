# Release Readiness

Status as of 2026-08-14: **static publication candidate, live validation
deferred**.
No commit, remote repository, history rewrite, or push is authorized by this
document.

Licensing sign-off was completed by the maintainer on 2026-08-18. The imported
code, queries, documentation, and selected result tables are authorized for
publication under `LICENSE` and `RESULTS_LICENSE`; supporting authorization
records remain private.

The maintainer elected to proceed with Git publication preparation without the
planned live smoke, portable-runner, and seven-system oracle phases. This does
not waive those checks: the development record continues to identify them as
known validation gaps.

## Static Gates Completed

- The canonical manifest contains 96 main, 15 Shortest Path, and 12 Update
  queries with current SHA-256 values.
- Adapter coverage has 861 explicit rows across seven systems; absent suites
  are marked `not_implemented`.
- Static semantic signatures pass for all 96 main translations, both static
  Shortest Path adapters, and GrainDB's 12 Update translations.
- `canonical_full_v1` names 30 source CSVs. Update's 16 directly referenced
  support tables have an untimed baseline derivation SQL file.
- Repository hygiene rejects likely credentials, private IPs, unapproved host
  paths, files over 10 MiB, and stale result/query hashes.
- Result artifacts for all seven systems are published under
  `results/<engine>/` with manifest provenance.

## Deferred Live Acceptance

| Adapter | Required release smoke test |
| --- | --- |
| AgensGraph | Load all 30 inputs; parse and execute 96 main queries; compare complete results to the DuckDB oracle. |
| ArangoDB | Load all 30 inputs; execute 96 main and 15 corrected Shortest Path AQL files with `arangosh`; compare complete results. |
| DuckDB | Build a clean full-profile database; derive Update staging; execute all 123 canonical files with the formal measurement contract. |
| GrainDB | Confirm loader schema and staging types; execute 96 main plus 12 Update files; validate graph syntax and baseline restoration. |
| Kuzu | Load and validate a healthy full-profile database; run all maintained runners; oracle-check results and explicitly exclude unresolved Update `4a/4b`. |
| OrientDB | On an exclusively opened healthy plocal copy, pass contract audit and preflight, then execute/oracle-check all 123 queries. |
| PostgreSQL | Load the full graph/table projection; execute 96 main queries, especially agtype/text joins; oracle-check complete results. |

Every smoke run must record DBMS version, configuration, data/query hashes,
row counts, skipped/dangling inputs, timeout, process tree, and output hashes.
Execution success alone is insufficient.

## Known Publication Limitations

1. AgensGraph, ArangoDB, DuckDB, GrainDB, and PostgreSQL still lack portable
   formal runners. Their retained shell scripts and loaders are historical.
2. No adapter has completed a post-reorganization live oracle run. ArangoDB's
   corrected Shortest Path AQL and GrainDB staging are highest-priority probes.
3. Kuzu Update `4a/4b` cannot preserve the relational incident-edge state with
   the current graph projection.
4. The previously observed legacy Git pack contained dataset blobs. It is not
   connected to this independent clean-history candidate and must never be
   imported into the public repository.
5. Published result files predate parts of the current query and measurement
   contract; their provenance notes remain in the result manifest.

## Final Local Gate

```sh
python3 tools/generate_manifests.py
git diff --exit-code -- benchmark/manifests results/manifests
python3 tools/audit_query_semantics.py
python3 tools/validate_repository.py --strict-paths
python3 -m compileall -q data scripts adapters tools
python3 -m unittest discover -s adapters/kuzu/tests -p 'test_*.py' -v
python3 -m unittest discover -s adapters/orientdb/tests -p 'test_*.py' -v
python3 -m unittest discover -s scripts/tests -p 'test_*.py' -v
python3 adapters/orientdb/tools/audit_benchmark_contract.py
```

Run shell syntax checks and `node --check` as defined in
`.github/workflows/validate.yml`, then follow
`docs/development/publication-checklist.md`. Committing, remote creation, and
publication require separate maintainer approval.
