# AgensGraph Adapter

This adapter publishes 96 static main-query translations and 15 audited
Shortest Path translations. `loaders/` and `runners/legacy/` are historical,
host-specific artifacts and are not formal portable entry points.

Twelve historical Update statements are published directly under
`queries/Update/`. They retain their source filenames and operation
direction, including legacy `3c.sql`; they are marked `legacy_adapter` and are
not claimed to implement the current canonical Update lifecycle.
