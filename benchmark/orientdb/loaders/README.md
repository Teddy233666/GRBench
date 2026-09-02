# OrientDB Loader

`load_orientdb_data.py` generates loader configuration from
`data/schema/sciscinet.py`, compiles `OrientDbCsvLoader.java`, creates the
database schema, imports data, records load provenance, derives Update staging,
and builds configured property indexes.
