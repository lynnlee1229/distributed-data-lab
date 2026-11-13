# 06 · Table snapshots, evolution and query responsibility

## Goal and prerequisites

Complete 02 and 04–05. Explain why files need table metadata, how mixed partition specifications coexist and where a query engine performs pruning. This is a reading / design extension, not an executed Iceberg deployment.

## A folder is not a committed table

Imagine a writer produces files A and B, then crashes before B appears. A reader listing a directory can observe an unintended subset. A table format adds metadata describing a particular committed set of data and delete files. In Iceberg, table metadata tracks snapshots and references; manifests describe file membership and statistics. A catalog participates in finding / committing table metadata. The precise atomic commit mechanism depends on the catalog and storage integration.

A snapshot selects file membership. It does not copy all data for every commit. Older snapshots may retain references to old files. Expiring snapshots and removing unreferenced files are maintenance operations with retention and concurrency conditions. Dropping an old-looking object by age alone can break a reader that still needs it.

## Schema and partition evolution

Field identity matters when names or positions change; stable field IDs can prevent confusing a new column with an old column at the same position. Partition evolution allows older files written under one specification and newer files under another to coexist. A planner interprets predicates under each relevant specification. Changing the specification is not proof that every old file was physically rewritten.

## The engine still has work

An analytical engine can prune at multiple levels: snapshot membership, partition / file metrics, Parquet Row Group statistics, perhaps page indexes, then exact row predicates. Each level has a different authority and granularity. Choosing columns reduces data requests independently from choosing rows. A table format does not execute SQL, and an engine does not make an arbitrary directory listing transactional.

HDFS can be one storage option; an object store can be another. This release does not create AWS resources or validate AWS semantics through a local compatible service. CockroachDB's transactional route remains separate from this file/table route.

## Data and design task

Write a tiny synthetic manifest on paper: snapshot S1 references A/B under month partitioning; S2 references A/B/C under day partitioning for C. For a one-day predicate, mark what can be rejected from partition metadata and what needs file statistics. Then add snapshot S3 that replaces B with D and decide whether B may be deleted while S1 is still retained.

## Expected result and interpretation

S2 can contain mixed specifications without rewriting A/B. A coarse month partition might keep a whole month as a candidate while the day-partitioned file is considered more precisely. Retained S1 still needs B. These are reasoning answers, not measured engine scans. For a fourth executable project, pin an Iceberg version, catalog and engine, record commit conflicts, inspect snapshot metadata and test old/new specifications; keep those observations separate from the three executed profiles here.

## Self-check

**Does a new snapshot require duplicating every Parquet file?** No. **Does partition evolution automatically rewrite history?** No. **Does an S3-compatible local API prove real AWS failure behavior?** No. **Can table-level pruning replace exact row filtering?** Usually not; candidate files may contain unmatched rows.

## Original sources

- [Iceberg table specification](https://iceberg.apache.org/spec/)
- [Iceberg evolution](https://iceberg.apache.org/docs/latest/evolution/)
- [Iceberg reliability and commits](https://iceberg.apache.org/docs/latest/reliability/)
- [Iceberg maintenance](https://iceberg.apache.org/docs/latest/maintenance/)
