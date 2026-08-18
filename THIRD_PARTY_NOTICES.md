# Third-Party Notices

GRBench interoperates with AgensGraph, ArangoDB, DuckDB, GrainDB, Kuzu,
OrientDB, and PostgreSQL. Those systems are not bundled and retain their own
licenses. Review the license of the exact version you install.

Python integrations use packages including `duckdb`, `kuzu`, `numpy`,
`pandas`, `psutil`, and `pyarrow`. Dependency files specify tested or bounded
versions but do not relicense those packages.

SciSciNet and any other benchmark input data are external artifacts. GRBench's
SciSciNet-v2 processing targets the Northwestern CSSI project:

- project: https://github.com/Northwestern-CSSI/sciscinet
- documentation: https://northwestern-cssi.github.io/sciscinet/
- SciSciNet paper: https://doi.org/10.1038/s41597-023-02198-9

As checked on 2026-08-18, the repository-level `LICENSE` and GitHub metadata say
BSD-3-Clause, while its README links to a separate MIT license. Treat the terms
of downloadable data artifacts as unresolved until the provider confirms which
license applies to the exact version used. GRBench does not redistribute those
artifacts.

The auxiliary generator scripts mention IMDb, MOOCCube, and DBLP. Their raw
data is not bundled and must be obtained under the provider's current terms.
The Apache-2.0 repository license and CC BY 4.0 results license do not grant
rights to redistribute any source dataset or model.
