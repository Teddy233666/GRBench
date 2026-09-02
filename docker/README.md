# Docker Environments

Copy `config/env.example` to `.env`, set non-empty passwords, and run Compose
from the repository root:

```sh
docker compose --env-file .env -f docker/compose.yml up -d \
  postgresql-age arangodb orientdb
```

These services pin the available image tags corresponding to the paper setup.
Their persistent state is written under `.local/docker/` and the processed SF
directories are mounted read-only at `/data/processed`. Verify the version from
inside every container before loading; the AGE image tag pins AGE and the
PostgreSQL major version, but an exact PostgreSQL 15.6 reproduction may require
a locally built image.

| System | Paper version | Docker status |
| --- | --- | --- |
| PostgreSQL + AGE | 15.6 + 1.6.0 | `apache/age:release_PG15_1.6.0`; verify/build PostgreSQL 15.6 exactly |
| ArangoDB | 3.12.4 | `arangodb:3.12.4` |
| OrientDB Community | 3.2.37 | `orientdb:3.2.37` |
| AgensGraph | 2.16 | No official 2.16 tag; set `AGENSGRAPH_IMAGE` to a locally built exact image. The Compose default 2.14.1 is compatibility-only. |
| DuckDB + DuckPGQ | 1.2.2 + `97a0c65` | Set `DUCKDB_IMAGE` to an image containing that DuckPGQ commit. The default image is SQL-only. |
| GRainDB | `be901b3` | Build the commit and tag it `grbench/graindb:be901b3`, or set `GRAINDB_IMAGE`. |
| Kuzu | 0.11.3 | Start the Python service and install the pinned wheel inside it. |

Compatibility/custom services are opt-in:

```sh
docker compose --env-file .env -f docker/compose.yml --profile compat up -d \
  agensgraph duckdb kuzu
docker compose --env-file .env -f docker/compose.yml --profile custom up -d graindb
docker exec grbench-kuzu pip install 'kuzu==0.11.3' 'psutil==7.2.2'
```

The OrientDB benchmark loader and runner use embedded plocal storage rather
than the server protocol. Run those commands in an image that contains Python,
Java 11, and the OrientDB 3.2.37 distribution, with the same database directory
mounted at `/orientdb/databases`. Do not let the server and embedded runner open
the same plocal database concurrently.
