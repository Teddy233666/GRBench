# Release Verification

A release candidate is acceptable only when:

1. `tools/validate_repository.py --strict-paths` passes from a clean checkout.
   This invokes `tools/audit_query_semantics.py`; CI also runs it explicitly.
2. Canonical counts are 96 main, 15 shortest path, and 12 Update; all hashes
   match and no `c` Update appears in canonical.
3. `canonical_full_v1` contains all 30 CSVs and every loader emits source,
   loaded, skipped, and dangling-endpoint counts plus input hashes.
4. Every supported adapter path in `adapter_coverage.csv` exists and every
   absence is explicitly `not_implemented`.
5. Engine smoke tests locate data, queries, configuration, and output roots
   without workstation-specific defaults.
6. Formal runs use one warmup, three measured runs, same-run median metrics,
   complete result consumption, one timeout policy, and Update baseline checks.
7. Correctness is verified against an independent result/state oracle before
   any artifact enters `results/comparable/`.
8. No dataset, database, build output, log, cache, credential, private address,
   or file above 10 MiB is present in the publication tree or filtered history.

Live smoke tests must be scheduled per engine. Never open a database that an
active loader or benchmark process already owns.
