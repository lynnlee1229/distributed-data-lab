# Validation record

Local validation completed on 2026-11-14 (Asia/Shanghai). The committed results are synthetic local measurements, not production or multi-host benchmarks.

- Parquet: all five files fully decoded and compared to one logical source; all 45 measured queries compared to the independent source-table predicate.
- Browser reader: real generated Footer fields checked against PyArrow, plus malformed footer, encrypted marker, missing statistics and unsafe integer bounds.
- HDFS: thirteen blocks at RF=3 before and after stopping one of four DataNodes; the stopped process remains stopped during verified read and repair checks.
- Database: three nodes and three replicas per range; distinct leaseholders and actual KV Put targets; transfer invariant, real 40001 and final business-rule invariant.
- Export: file hashes, local links, translation pairs, isolated ZIP and privacy-marker checks.

See results/index.json for hashes and docs/reproduce.en.md for methodology. Raw runtime logs and node stores are intentionally excluded. Publication, CI and browser verification are recorded separately in the local release evidence; no unobserved check is claimed here.

Final native baseline: Python 3.11.2 / PyArrow 20.0.0; HDFS 3.4.2 with OpenJDK 11.0.15; CockroachDB 24.1.24 arm64. HDFS final state is 3 live / 1 dead, 0 under-replicated and 0 pending-reconstruction blocks; every one of 13 blocks has 3 live copies. Database KV trace shows Put requests to distinct nodes and the executed scan plan lists n1, n2, n3. Four semantic evidence tests and four browser-parser tests pass. The exported ZIP was extracted independently, its Parquet profile executed, tests run and site rebuilt. Desktop and 390px mobile pages were inspected; no document-level horizontal overflow was found on the tested course/evidence pages.

Environment isolation: the HDFS runner removes inherited Hadoop configuration variables, selects and verifies JDK 11, and assigns each node its own PID directory and identity. This avoids mixing installed versions and the upstream shell’s default shared PID-file race. Raw failure logs remain local and are excluded from publication.
