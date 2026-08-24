# Kuzu Loader

`load.py` creates the Kuzu schema, projects canonical CSVs into staging where
needed, loads nodes and relationships, and reports counts. Node primary keys
provide Kuzu lookup indexes; there is no separate index script.
