# ArangoDB Pure Join Coverage

This directory publishes all 96 AQL files. For 72 implementations, static
anchors, predicates, and logical relation dependencies match the canonical
Pure Join queries. The other 24 are requested authoritative legacy files and are
marked `legacy_unverified` because they fail the semantic signature audit.

The unverified groups are `2a-c`, `11a-c`, `13a-c`, `16a-c`, `17a-c`,
`23a-c`, `31a-c`, and `32a-c`. Apply semantic corrections and run a live
result-oracle comparison before treating their results as comparable.
