# PostgreSQL Adapter

This adapter publishes 96 static main-query translations. Shortest Path and
Update are not currently published as audited formal adapter queries. Loader
helpers and shell runners are retained as historical implementation evidence.

The historical CSV preparation helpers require the packages in
`adapters/postgresql/requirements.txt`. On Debian/Ubuntu, install the LevelDB
headers (`libleveldb-dev`) before installing `plyvel`. These helpers are not a
portable formal runner.
