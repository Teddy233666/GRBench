# AgensGraph Update Queries

The SQL files in this directory are direct copies of the retained server directory
`tasks/agensgraph_task/update/Update/`. Their SQL text is intentionally not
rewritten.

They use the historical operation convention, which differs from the current
canonical GRBench lifecycle. The source provides `3c.sql` instead of `3b.sql`;
the adapter manifest maps canonical inventory ID `update/3b` to `3c.sql` while
marking every AgensGraph Update row as `legacy_adapter`.

These files are published for execution/provenance access, not as
canonical-equivalent or cross-system-comparable Update implementations.
