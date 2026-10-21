# PostgreSQL Shell Runners

These compatibility entry points retain the historical hot-`psql` execution
model while using current repository paths and environment-based connections.

| Entry point | Suite | Runs |
| --- | --- | ---: |
| `run_main_three_rounds.sh` | 96 AGE main queries | 3 |
| `run_relational_three_rounds.sh` | 96 RH/RG plus 15 relational S equivalents | 3 |
| `run_update_three_rounds.sh` | 12 AGE Update queries | 3 |
| `run_update_single_round.sh` | 12 AGE Update queries | 1 |

Use `--list` to inspect the ordered inventory without opening PostgreSQL. Set
`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USERNAME`, and
`POSTGRES_PASSWORD` in the environment. `GRBENCH_POSTGRESQL_RESULT` overrides
the default result path.

Update restore files are rendered under the server-visible directory named by
`GRBENCH_POSTGRES_UPDATE_PREPARED_ROOT`. Each `b` query runs its paired `a`
query as unmeasured setup; every measured Update is enclosed in a transaction
and rolled back before the next query.

CPU samples include PostgreSQL/postmaster processes visible on the host. RSS
uses those processes by default. Set `POSTGRES_CGROUP_PATH` only when it points
to a dedicated PostgreSQL cgroup; otherwise unrelated processes would pollute
the measurement. Three-round runners select the complete run with median
elapsed time, keeping CPU, RSS, result, and status from that same run.

The source-only `postgresql_benchmark_common.sh` is shared implementation and
must not be executed directly. These scripts still require live result-oracle
and AGE transaction tests before their output is considered formal.
