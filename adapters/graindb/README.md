# GrainDB Adapter

This adapter publishes 96 main and 12 Update SQL translations. Shortest Path
is not currently published. Before running Update, derive its support tables
with `benchmark/setup/derive_update_staging.sql`; the retained loader does not
create them. The loader and shell runners are historical and must not be
treated as portable formal entry points.
