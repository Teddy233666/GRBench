# Repository Guidelines

## Project Structure & Module Organization

`benchmark/queries/canonical/` is the authoritative 123-query SciSciNet suite.
`benchmark/schema/` defines the 30-CSV `canonical_full_v1` input contract, and
`benchmark/manifests/` records hashes, aliases, Update lifecycles, and adapter
coverage. Engine code lives under `adapters/<engine>/`; keep generated
databases and CSV staging in `.local/`. Curated artifacts belong in
`results/latest-observed/`, while only contract-compliant results may enter
`results/comparable/`. Superseded query variants belong in `legacy/`.

## Build, Test, and Development Commands

Regenerate deterministic manifests after query, coverage, or result changes:

```sh
python3 tools/generate_manifests.py
```

Run the repository's database-free validation gate:

```sh
python3 tools/validate_repository.py --strict-paths
```

Audit stable query signatures independently while editing translations:

```sh
python3 tools/audit_query_semantics.py
```

Compile Python sources without running a DBMS:

```sh
python3 -m compileall -q benchmark adapters tools
```

Engine commands are documented in `docs/systems/`; do not open an active
OrientDB plocal database from a second process.

## Coding Style & Naming Conventions

Use Python 3.10+, 4-space indentation, type hints for new public functions,
and `snake_case` names. Preserve query IDs such as `16b.sql` across canonical
and adapter paths. Keep engine-specific syntax in its adapter; shared workload
facts belong in `benchmark/`. Use repository-relative paths or environment
variables, never workstation-specific absolute path defaults.

## Testing Guidelines

Every canonical query change must update its SHA-256 manifest and all affected
adapter translations. Check anchors, thresholds, edge direction, optional vs.
inner semantics, output aliases, and Update setup/compensation. Formal runs use
one warmup plus three measured runs and select all metrics from the median-time
run. Do not treat execution success alone as semantic correctness.

## Commit & Pull Request Guidelines

Use short imperative commits, for example `fix arangodb optional joins`.
Pull requests must state affected queries/systems, commands run, data profile,
and result comparability impact. Never commit datasets, database files, logs,
build output, credentials, private addresses, or unreviewed generated results.
Do not rewrite imported history or push a release without maintainer approval.
