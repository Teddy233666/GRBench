# Query Semantic Audit

## Canonical Corrections

The release canonical snapshot intentionally differs from the earlier source
checkout in seven places:

| Query | Earlier form | Canonical form | Reason |
| --- | --- | --- | --- |
| `16b` | `citation_count < 180` | `< 80` | align the `b` selectivity tier |
| `18b` | `citation_count < 100` | `< 80` | align the `b` selectivity tier |
| `26c` | `citation_count = 2` | `= 1` | align the `c` predicate |
| `29c` | `m2.h_index >= 1000` | `>= 1500` | restore the high threshold |
| `32a` | two inner joins | two left joins | preserve optional branches |
| `32b` | inner joins and trailing comma | left joins, valid select list | preserve optional branches and syntax |
| `32c` | inner joins and trailing comma | left joins, valid select list | preserve optional branches and syntax |

## Syntax-Only Normalization

`20a.sql`, `20b.sql`, and `20c.sql` had a comma immediately before `FROM`.
The comma was removed, and the `20c.sql` anchor literal was normalized from a
line-broken string to `W2122344208`. These repairs do not change the intended
query predicates or join structure and are not additional semantic revisions.

The 12 authoritative Update files are the `1a..6b` files under
`benchmark/queries/canonical/update/Update/`. Old `c` variants are excluded.
Update `3b` preserves both author-paper directions; adapters that collapse the
physical representation must reverse `authorid,paperid` endpoints explicitly.

## Additional Adapter Corrections

- AgensGraph `16b` previously joined Nobel rows to `ref_paperid`; canonical SQL
  joins them to the anchored `paperid`.
- ArangoDB `18b` previously used nested `FOR` loops for Newsfeed and Nobel,
  turning two optional branches into inner joins. It now computes nullable
  scalar aggregates without filtering the main path.
- ArangoDB Shortest Path `1a-c` and `4a-c` returned the fixed start ID instead
  of the endpoint minimum. `2a-c` and `5a-c` implemented unrelated workloads,
  and `3a-c` returned a custom object after an inner traversal. All 15 files
  now preserve the canonical endpoint, predicate, hop bound, and aggregate.

`tools/audit_query_semantics.py` compares anchors, selected numeric predicates,
and logical edge dependencies for all 96 static main-query translations and
the published Pure Join variants. It also checks the 15 static Shortest Path
adapters, the ArangoDB hop-family invariants, GrainDB's 12 Update files, and a
high-risk OrientDB endpoint mapping. This is a regression gate, not proof of
full result equivalence.

The Pure Join restoration audit found no signature drift in the authoritative
AgensGraph, DuckDB, GrainDB, and PostgreSQL files. OrientDB required corrections
to `13a-c`, `17a-c`, `26c`, and `29c`. ArangoDB has 72 audited files plus 24
requested `legacy_unverified` files; see `docs/development/pure-join-audit.md`.

Static review cannot prove result equivalence on every engine. Promotion to
`comparable` still requires an oracle run against healthy full-profile data.
