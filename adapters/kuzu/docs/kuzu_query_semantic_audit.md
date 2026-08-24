# Kuzu Query Semantic Audit

Date: 2026-07-06

## Scope

- Original SQL: `benchmark/queries/canonical`
- Kuzu main Cypher: `adapters/kuzu/queries`
- Excluded duplicate result suite: `Pure_Join_Queries`
- Audited main query pairs: 96 SQL files and 96 Cypher files
- Audited generated suites: `Shortest_Path_Queries` and `update/Update`

## Main Query Findings

The main 96 Kuzu Cypher files now have one-to-one file coverage with the original 96 non-duplicate SQL files. The review checked path shape, anchor constants, filter thresholds, join direction, optional-vs-inner semantics, and returned aggregate columns.

Known previous mismatches were corrected in the 96 published Cypher files.
These included wrong NIH/NSF metadata join keys, wrong 12a-12c
`hit_papers_level1` mapping, wrong 23a-23c output alias, wrong 25b/25c/29c
h-index filters, wrong 32a-32c inner join semantics, and several Low-Join
threshold/anchor/join-target errors. Duplicate `Pure_Join_Queries` files are no
longer published; their logical aliases are recorded in the shared manifest.

No residual known-bad patterns were found for those cases.

## Update Findings

The Update runner now better matches the original DuckDB Update SQL:

- `3a.sql` explicitly deletes `PaperReferences`, `Papers_to_Authors`, `contributed_from`, `PaperFields`, link tables, `link_twitter`, then `Papers`.
- `3b.sql` restores both paper-author insert sources. The original SQL inserts `Papers_to_Authors` from `grbench_update1_papers_to_authors` and also inserts `Authors_Paper` from the update3 author-paper source. Kuzu represents both as the single `Papers_to_Authors` relation, so the update3 source is rewritten from `authorid,paperid` to `paperid,authorid` and copied into `Papers_to_Authors`.
- `6a.sql` explicitly deletes `Papers_to_Authors`, `affiliated_with`, then `Authors_Gender`.
- Insert tasks `1b/2b/3b/4b/5b/6b` run their delete setup before timing the insert, in both normal and warm RSS runners.

Maintained implementation: `adapters/kuzu/runners/run_update.py`.

## Shortest Path Findings

The Shortest Path runners are aligned with the corrected original directory:

- `benchmark/queries/canonical/Shortest_Path_Queries`

Kuzu does not directly support SQL/PGQ `ANY SHORTEST`, so the runners evaluate exact path depths and aggregate endpoint `MIN` values. For `{1,}` and `{,}` patterns, the implementation is bounded by `--max-unbounded-depth` with default `8`; this is an implementation limit and should be reported with the benchmark results.

## Verification

Commands run:

```sh
python3 -m py_compile adapters/kuzu/runners/run_shortest.py adapters/kuzu/runners/run_update.py
python3 tools/audit_query_semantics.py
```

## Remaining Caveats

- Kuzu uses graph-oriented schema mappings, so some relational tables are represented as node tables plus explicit joins in Cypher.
- `Authors_Paper` in original SQL is represented by Kuzu's `Papers_to_Authors` relation. Query rewrites must reverse endpoints when the source file is ordered as `authorid,paperid`.
- `PaperDetails` and `Twitter_Metadata` are not broadly used by the audited main query set, but any future query touching those tables must be rechecked against the loader schema.
- Existing benchmark result files generated before this audit may include results from older query or runner semantics and should not be treated as final without rerun or provenance filtering.
