# 06 · Real table snapshots, evolution and time travel

## Goal and prerequisites

Complete 02 and 04–05. Explain why valid files need table membership metadata, then verify a real table's retained rowsets, field identity and mixed partition specifications. This chapter has an executed **PyIceberg 0.10.0 / table-format v2** profile, with a local SQLite catalog and filesystem. SQLite is a development catalog here, not a distributed transaction service.

## Commit a set of files, not a directory listing

A file can be perfectly valid Parquet and still belong to no committed version of a table. Iceberg metadata identifies snapshots; manifests describe the files selected by each snapshot. A catalog identifies the current metadata pointer. Reading every file found below a directory bypasses that membership decision.

Our negative control writes a valid Parquet file containing id=999 directly into the table's data directory, without committing it. PyArrow reads the file successfully. A naive union of all physically listed file IDs includes 999. A real Iceberg scan returns only ids 1–6 because no committed manifest references the extra file. The exercise leaves it in place and does not expire snapshots or delete files.

## Run from zero

```sh
pip install -r requirements-iceberg.txt
python lab.py iceberg
python scripts/validate_iceberg.py results/iceberg.json
```

No JVM, Docker, cloud account, API key or remote catalog is needed. All inputs are six enumerated synthetic records; a seventh record is the explicit uncommitted control. Each run creates its own build/iceberg directory. `experiments/iceberg_snapshots.py` contains separate writer batches and literal expected rowsets. The validator independently checks the reported contract. Read the complete saved report on the evidence page.

## Predict before running

| Step | Prediction to check |
| --- | --- |
| Append three rows | First data snapshot has exactly ids 1,2,3 |
| Append two rows | Second snapshot has ids 1–5; first remains readable |
| Rename category to topic; add optional quality | Field ID 2 persists; old records yield null quality |
| Add identity partitioning on topic | Existing files retain spec 0; only new files use spec 1 |
| Append id=6 | Third data snapshot has six rows under the evolved schema |
| Write valid id=999 outside the table commit | Directory union includes it; Iceberg membership excludes it |

A rename updates a field's name while retaining its identity. It does not rewrite old Parquet bytes. The experiment reads physical Parquet field metadata: two old files still name the field `category`, the new file names it `topic`, and both use field ID 2. Current Iceberg projection resolves the renamed field correctly. SHA256 hashes verify that the old files did not change during the metadata operations.

## A schema commit is not a data snapshot

The schema change writes a new table metadata version while keeping the second data snapshot ID unchanged. In this pinned PyIceberg reader, `scan()` projects the current table schema; `scan(snapshot_id=...)` selects the stored snapshot schema. Immediately after the schema-only commit, those calls can read the same data membership through different column names. The recorded rows and before/after IDs make this visible.

This is an observed PyIceberg 0.10.0 API behavior, not a promise that every SQL engine applies the same time-travel schema policy. State the reader version and projection when comparing results.

## Actual results and metadata checks

The three data snapshots contain **3 / 5 / 6 rows** with a verified parent chain. Historical scans after the later commits equal the literal earlier expected rowsets. Their canonical rowset hash stays unchanged. Latest has a different hash; hashes include column names, so the report defines normalization precisely.

The final file plan includes partition spec IDs **0 and 1**. For `topic = 'storage'`, the old unpartitioned file with possible matching rows remains a candidate, while file statistics can reject another old file. Exact row filtering returns ids **1,3,6**. A plan lists candidate files; it is not an actual disk-I/O counter.

A fresh catalog object reloads the SQLite pointer and reads the same final rows. The report also checks actual metadata JSON for format version, current schema/spec/snapshot, parent IDs and record counts. Public evidence contains an allowlist of these fields and relative synthetic file names; full metadata and the catalog remain local because raw locations can include machine paths.

## A folder is not a table, and a table is not an engine

A snapshot reuses files; it does not copy the complete dataset on every commit. Retained snapshots can still reference old files, so deleting objects by apparent age can break reads. This experiment performs no destructive maintenance. It validates one local library/catalog/file combination, not catalog concurrency, crash atomicity, object-store failure behavior, delete-file interoperability or production capacity.

HDFS is one storage route, and object storage is another. Iceberg is a table format, Parquet is a file format and the reader plans and evaluates the scan. This profile uses local files and never claims AWS behavior.

## Hands-on task

Change only the last appended topic, predict the filtered rowset and inspect file spec IDs again. Then rename a second field and observe the current versus pinned projection before adding new data. Keep the old file hashes and literal expected rows; do not weaken assertions to accept an unexplained change. All of these are original Lab exercises, not university assignment solutions.

## 2026 reading extension: data lineage for retrieval

MIT's published Spring 2026 Lecture 17 covers embeddings, RAG and vector databases. Our connection is an engineering inference: a retrieval-index build should record its source snapshot, schema, preprocessing version and model version. This experiment proves stable data membership for a pinned snapshot and a moving latest view. It does not create embeddings, call an LLM or measure retrieval quality.

## Self-check

**Did the schema-only update create a fourth data snapshot?** No. **Why can physical files still say category?** Field identity permits a logical rename without rewriting them. **Does a local SQLite catalog prove a distributed catalog is safe?** No. **Why is id=999 excluded?** It is absent from committed manifests, not an invalid Parquet row. **Can a new partition spec rewrite all old files automatically?** This experiment shows the old spec survives unchanged.

## Guided university reading and original exercise

- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 20 / 2026-04-28 · Cloud DB](https://dsg.csail.mit.edu/6.5830/lectures/lec20.pdf)
- [Apache Iceberg · Schema evolution; Partition evolution; Query the data · PyIceberg API: schema evolution, partition evolution and scans](https://py.iceberg.apache.org/api/)
- [Apache Iceberg · SQL Catalog; Development only · PyIceberg configuration: SQL Catalog / SQLite](https://py.iceberg.apache.org/configuration/#sql-catalog)
- [Apache Iceberg · Snapshots; Schemas; Partition specs; File metadata · Iceberg Table Specification](https://iceberg.apache.org/spec/)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 17 / 2026-04-14 · Embeddings, RAG, and Vector DBs](https://dsg.csail.mit.edu/6.5830/lectures/lec17.pdf)

Create real snapshots, rename a field by identity, evolve a partition spec and compare a pinned read with a naive directory listing.

```sh
pip install -r requirements-iceberg.txt
python lab.py iceberg
```

Snapshot rowsets 3/5/6; field ID 2 survives rename; file specs 0 and 1 coexist; old hashes persist; uncommitted id=999 stays outside the table.

These are original Lab exercises, not the universities’ assignment solutions. Public reading access does not grant enrollment, credit or grading. See the searchable resource library for prerequisites and verification dates.

## Original sources

- [PyIceberg 0.10.0 release](https://github.com/apache/iceberg-python/releases/tag/pyiceberg-0.10.0)
- [PyIceberg API: schema, partition evolution and scans](https://py.iceberg.apache.org/api/)
- [SQL Catalog / SQLite development scope](https://py.iceberg.apache.org/configuration/#sql-catalog)
- [Iceberg table specification](https://iceberg.apache.org/spec/)
- [MIT Spring 2026 Lecture 20: Cloud DB](https://dsg.csail.mit.edu/6.5830/lectures/lec20.pdf)
- [MIT Spring 2026 Lecture 17: Embeddings, RAG, and Vector DBs](https://dsg.csail.mit.edu/6.5830/lectures/lec17.pdf)
