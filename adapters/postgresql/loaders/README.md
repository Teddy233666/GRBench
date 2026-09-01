# PostgreSQL/AGE Loaders

`load.py` is the maintained loader for all five SciSciNet scale factors. It
uses the canonical 30-CSV schema inventory and exposes relational PostgreSQL
and Apache AGE projections through one CLI.

Render a plan without opening PostgreSQL:

```sh
python3 adapters/postgresql/loaders/load.py plan \
  --sf sf10_0 --projection relational --rebuild
```

Execute a fresh relational load:

```sh
python3 adapters/postgresql/loaders/load.py load \
  --sf sf10_0 --projection relational --rebuild
```

Set `POSTGRES_PASSWORD` in the process environment or an ignored local env file
before executing the load command.

AGE requires a preparation phase. Prepared files contain label-local IDs and
edge endpoint mappings expected by AGE's bulk loaders:

```sh
python3 adapters/postgresql/loaders/load.py prepare-age \
  --sf sf10_0 --orphan-edge-mode fail
python3 adapters/postgresql/loaders/load.py load \
  --sf sf10_0 --projection age --rebuild
```

The default orphan policy is `fail`. `skip` is permitted only for an explicitly
documented audit and records skipped/missing endpoint counts in
`prepare_manifest.json`. If PostgreSQL runs on another host or container, pass
`--server-prepared-root` with the path visible to that server.

Load plans, preparation outputs, LevelDB maps, logs, and resumable manifests
belong under `.local/`. The former SF-specific SQL templates and table-specific
Python preprocessors have been removed; repository history retains their
provenance when an old experiment must be inspected.
