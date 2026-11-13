# 01 · Names, bytes and authority

## Goal and prerequisites

Start here. Know what a byte and a directory are. After this chapter, place a system at its correct layer and explain who knows where data lives.

## A name is not its content

A file exposes a byte sequence, a path and filesystem operations. A distributed filesystem divides that sequence into blocks and keeps a mapping from names to blocks to replicas. An object store exposes keys and whole objects through an API. An object's key can look like a directory, but that spelling does not promise filesystem rename semantics. Changing a key can require different operations from renaming a file.

Metadata is data about data, but its authority matters. A Parquet footer describes one file's schema and layout. A NameNode maps a namespace and block locations. A table catalog can identify the committed table metadata. None of these can automatically substitute for the others.

## Two routes, different contracts

| Layer | Analytical file route | Transactional key route |
| --- | --- | --- |
| API / execution | A SQL engine plans scans | A SQL gateway plans reads and writes |
| Logical organization | Iceberg may track table snapshots | Database indexes map rows to key ranges |
| Local representation | Parquet stores column chunks | MVCC versions are held in an LSM engine |
| Durability / placement | Local files, HDFS or object storage | Replicated ranges on database nodes |

These are examples of compatible roles, not a universal deployment diagram. Parquet can sit on a local disk without Iceberg. Iceberg can reference Parquet on an object store without HDFS. CockroachDB's normal transactional storage does not route through HDFS or Parquet. HDFS and S3 are storage systems; Parquet is a file format; Iceberg is a table format; an engine executes queries; a distributed database also owns transactional coordination and placement.

## Data and code

All executable examples use synthetic bytes or seeded rows. Open `experiments/parquet_layout.py` and find the schema. Sketch four metadata records: file footer, block-location map, snapshot reference, primary-index key range. Give each a different identifier.

## Hands-on task

For “find rows where id is between 32000 and 33023”, write the sequence of decisions: choose a committed table version if applicable; choose files; fetch footer; prune row groups; read required chunks; decode; apply the exact row predicate. Mark which decisions disappear for a standalone file.

## Result and interpretation

The executable coverage begins in chapter 02. This chapter is a classification exercise, with no storage benchmark. A correct answer does not insert a catalog or HDFS into a standalone Parquet read. Footer statistics can eliminate impossible groups, but cannot establish table-level atomic commit.

## Self-check

**Can a valid Parquet file represent a half-published table?** Yes. Individual file validity does not identify the committed set of table files. **Is a Row Group an HDFS block?** No. One is a file-format grouping; the other is a storage allocation / replication unit. Their boundaries need not align.

## Original sources

- [Parquet concepts](https://parquet.apache.org/docs/concepts/)
- [HDFS architecture, 3.4.2](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [S3 objects and keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingObjects.html)
- [Iceberg specification](https://iceberg.apache.org/spec/)
