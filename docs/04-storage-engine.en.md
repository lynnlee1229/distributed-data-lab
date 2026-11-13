# 04 · WAL, LSM, MVCC and the cost of an index

## Goal and prerequisites

Complete 01–03. Know primary keys and transactions. Separate recovery, layout, version visibility and distributed agreement. This chapter is a reading / reasoning bridge; it does not claim to measure compaction or crash recovery.

## Four mechanisms, four questions

A write-ahead log records changes before their durable application to other structures. It supports recovery, subject to the actual sync policy and failure model. An LSM engine collects writes in memory, flushes sorted tables and compacts them later. Moving work from immediate updates to background merging trades write, read and space amplification. “Sequential writes” does not make every LSM workload cheap.

MVCC keeps multiple versions so readers can choose a consistent visibility point. Old versions need retention and reclamation rules. A snapshot protects a view; it does not mean every concurrent read-modify-write sequence can commit safely. Serializable execution requires additional conflict control.

Replication agreement addresses copies on different nodes. Raft log entries and an engine WAL have different roles, even when both are logs. A majority acknowledging a command and a transaction deciding all participant updates form different protocol layers. Neither is equivalent to putting a file in HDFS.

## Index keys become placement keys

A row's primary index stores its encoded key/value representation. A secondary index introduces more keys, often elsewhere in the sorted keyspace, so one logical row update can touch more than one range. A range is a contiguous key interval; each range can be replicated. A leaseholder serves particular request responsibilities while replicas maintain the range. More ranges do not create unlimited independent capacity: a single hot key still belongs to one range at a time.

The next experiment uses a real CockroachDB 24.1.24 baseline with Pebble, MVCC and replicated ranges. The preserved evidence checks range placement and transaction outcomes; it does not inspect Pebble SSTables or prove fsync behavior.

## Data and code

Read the accounts table in `experiments/distributed_transactions.py`. Three primary keys intentionally fall into separate intervals split at 1000 and 2000. Only three account rows are needed to test transaction correctness; a large dataset would obscure the schedule.

```sql
CREATE TABLE accounts (
  id INT PRIMARY KEY,
  balance INT NOT NULL CHECK (balance >= 0)
);
ALTER TABLE accounts SPLIT AT VALUES (1000), (2000);
SHOW RANGES FROM TABLE accounts WITH DETAILS;
```

## Hands-on task and expected result

Sketch an index entry for a primary key and a hypothetical secondary index on balance. List what changes during a transfer. Then distinguish these statements: “the row is durable locally”, “the range replicated its command”, “the transaction committed”, “a snapshot can observe the new version”. They need separate evidence. This is a paper exercise; the only measured claims are linked from chapter 05.

## Self-check

**Does MVCC eliminate write conflicts?** No. **Does adding a secondary index have zero write cost?** No; extra keys and coordination may be required. **Can compaction delete every older version immediately?** No; active readers and retention rules may need them. **Can a range split alone solve one hot key?** No; the key's traffic remains concentrated.

## Original sources

- [CockroachDB storage layer](https://www.cockroachlabs.com/docs/v24.1/architecture/storage-layer)
- [CockroachDB replication layer](https://www.cockroachlabs.com/docs/v24.1/architecture/replication-layer)
- [CockroachDB transaction layer](https://www.cockroachlabs.com/docs/v24.1/architecture/transaction-layer)
- [Pebble project and documentation](https://github.com/cockroachdb/pebble)
