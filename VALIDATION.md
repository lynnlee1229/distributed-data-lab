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


## Depth iteration: executed local table semantics

The selected gap was chapter 06's lack of executed table-format semantics. A bounded local Iceberg profile now checks actual snapshots, metadata-only schema and partition commits, stable field ID across rename, old file immutability, time travel and persisted SQLite catalog state. The counterexample is a valid Parquet file never committed to a manifest; only raw directory enumeration sees its id=999. No destructive table maintenance or external service is used.

The formal `python lab.py iceberg` entry and independent report validator were run from the documented commands. Earlier candidate and repeat executions agree on canonical historical/current rowset hashes. False-success mutations remove the directory counterexample, change the schema-only snapshot, alter current/old rows or rewrite a retained file hash; the independent checker rejects them. The original three measured result files are preserved byte-for-byte against the v1 manifest.

The structured resource inventory covers two official university offerings, nineteen exact source records and all six learning units. Twenty-five official URLs (including course metadata) were fetched successfully as public HTML/PDF prefixes on 2026-11-14 Asia/Shanghai. The GFS paper is labeled 2003; MIT Lecture 17 is an actually published Spring 2026 PDF. No university content/solutions are mirrored and no enrollment/fee inference is made. Search and filters use this local inventory.

The profile validates PyIceberg 0.10.0 / table format v2 with a local SQLite catalog and filesystem. It does not test distributed catalog concurrency, crash atomicity, cloud APIs, delete-file interoperability, embeddings or RAG quality. Current versus explicit-snapshot schema selection is recorded as reader-version-specific behavior.
