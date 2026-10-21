# Query Naming

Query filenames follow the series names in Table 1 of the GRBench paper
(arXiv:2608.31027v1).

| Series | Files | Meaning |
| --- | --- | --- |
| H | `H1a`-`H24c` | Graph-relational hybrid queries |
| G | `G1a`-`G8c` | Pure graph queries |
| S | `S1a`-`S5c` | Shortest-path operator queries |
| RH | `RH1a`-`RH24c` | Relational equivalents of H |
| RG | `RG1a`-`RG8c` | Relational equivalents of G |
| U | `U1a`-`U6b` | Update capability queries |

Suffixes `a`, `b`, and `c` in H, G, S, RH, and RG denote the three
predicate-selectivity variants. For U, suffix `a` is deletion and suffix `b`
restores the same records.

## Update Reordering

The legacy Update numbering interleaved operation types. The paper groups
templates by semantics, so Update files use this explicit map:

| Legacy pair | Paper pair | Operation |
| --- | --- | --- |
| `1a/1b` | `U1a/U1b` | Paper vertices |
| `4a/4b` | `U2a/U2b` | Author vertices |
| `2a/2b` | `U3a/U3b` | Paper-reference edges |
| `5a/5b` | `U4a/U4b` | Paper-author edges |
| `3a/3b` | `U5a/U5b` | Papers and incident edges |
| `6a/6b` | `U6a/U6b` | Authors and incident edges |

The complete 219-ID migration is recorded in
[`query-name-map.csv`](query-name-map.csv). Result files produced before this
rename must be translated with that map before comparison.
