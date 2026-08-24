# AgensGraph Shortest Path Queries

These 15 translations were migrated from the server-side AgensGraph workload
snapshot at `tasks/agensgraph_task/shortest_path/`.

The migrated `3a.sql`, `3b.sql`, and `3c.sql` replace the source snapshot's
physical aliases `Affiliation`, `affl_assoc_affls`, and
`contributed_from_new` with the public loader names `Affiliations`,
`affl_assoc_affl`, and `contributed_from`. No predicates, anchors, hop bounds,
join type, or output aggregation were changed.

Static signature validation is performed by `tools/audit_query_semantics.py`.
Formal publication of measurements still requires execution against a database
built by the public loader and complete-result oracle comparison.
