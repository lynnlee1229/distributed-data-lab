# 05 · Transactions across ranges and nodes

## Goal and prerequisites

Complete 04. Know BEGIN / COMMIT and a read-modify-write cycle. Verify actual range placement, commit across ranges and observe a real serialization conflict.

## Distribution has to be observed

Three SQL connections to one standalone database are not a distributed database experiment. Here, three independent CockroachDB processes join one cluster. Each has an exclusive persistent directory and loopback SQL / HTTP ports. The experiment waits for three replicas on each account range, deliberately relocates leases, then reads placement back. Distinct leaseholders demonstrate distinct serving nodes, while all processes still share one physical host.

A SQL gateway can coordinate operations against multiple ranges. The primary keys 1, 1001 and 2001 cross the split boundaries. A transfer subtracts 7 from id=1 and adds 7 to id=1001 within one transaction; the total must stay 300. KV trace and an executed aggregate plan help inspect the real request path. They are evidence of execution, not a network packet capture or proof of every crash scenario.

## A conflict without updating the same row

The business rule requires total balance to remain at least 220. Clients A and B both read total=300. A subtracts 80 from id=1; B subtracts 80 from id=1001. Each would leave 220 if it were alone. If both committed using the stale total, only 140 would remain. Their writes are disjoint, yet their decisions depend on overlapping reads: this is write skew.

The experiment uses SERIALIZABLE transactions, returns each total to its client before updates and commits concurrently. One commit succeeds; the other must require a retry with SQLSTATE 40001. The database is not configured to inject retry errors. The committed result sums to 220. A complete business retry reads the fresh total and declines the second withdrawal. Replaying only the last UPDATE would ignore the original decision rule.

## Data and executable code

```sh
python scripts/bootstrap.py database
python lab.py database
```

Read `experiments/distributed_transactions.py` for the exact schedule, connections, assertions, KV trace and metrics. The evidence page keeps both outcomes, balances, placement, plan and counter snapshots. Error messages may vary with which transaction wins; the invariants do not. Tiny timing differences are not a throughput comparison.

## Actual results and interpretation

Check three live node IDs, three replicas per range and distinct leaseholders. Verify transfer balances [93,107,100], unchanged sum 300, one 40001 outcome and final sum 220. The losing transaction may be A or B, so final individual balances can differ between runs. Counter changes include setup and measurement queries; they are supporting context rather than a precise per-transaction attribution.

## Hotspot extension: reasoning, not measured capacity

Sequential keys can concentrate writes in an edge range. Pre-splitting helps distribute ranges when the key distribution reaches them; it does not scatter a single hot key. A wider index also changes the cost of one logical write. To study a hotspot, vary a deterministic key distribution and capture range-specific rates and lock contention. This release measures the conflict schedule instead; it does not claim a hotspot benchmark.

## Hands-on task

Reverse which key each client updates. Keep the invariant checks. Replace the total read with a read of only its own account and explain why the business rule loses protection. Do not remove 40001 handling from real application code: retry the complete transaction with a bounded policy and re-evaluate its business condition.

## Self-check

**Does a single successful transfer prove atomicity under a node crash?** No; no crash was injected here. **Why inspect leaseholders as well as replicas?** Copies and serving responsibilities differ. **Is a retry error a broken guarantee?** Here it is the mechanism that prevents an invalid serializable history.

## Guided university reading and original exercise

- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 12 / 2026-03-19 · Optimistic Concurrency Control, Snapshot Isolation](https://dsg.csail.mit.edu/6.5830/lectures/lec12.pdf)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 15 / 2026-04-07 · Distributed Databases](https://dsg.csail.mit.edu/6.5830/lectures/lec15.pdf)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 16 / 2026-04-09 · Distributed Transactions](https://dsg.csail.mit.edu/6.5830/lectures/lec16.pdf)
- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #20 · Multi-Version Concurrency Control](https://15445.courses.cs.cmu.edu/fall2025/slides/20-multiversioning.pdf)

Run the transfer and stale-total write-skew schedule, then retry the entire business decision against the fresh total.

```sh
python scripts/bootstrap.py database
python lab.py database
```

KV Put trace reaches distinct serving nodes; transfer total=300; one real 40001; final total=220; the second withdrawal is declined.

These are original Lab exercises, not the universities’ assignment solutions. Public reading access does not grant enrollment, credit or grading. See the searchable resource library for prerequisites and verification dates.

## Original sources

- [Local cluster deployment](https://www.cockroachlabs.com/docs/v24.1/start-a-local-cluster)
- [SHOW RANGES](https://www.cockroachlabs.com/docs/v24.1/show-ranges)
- [ALTER RANGE lease relocation](https://www.cockroachlabs.com/docs/v24.1/alter-range)
- [Transaction retry errors](https://www.cockroachlabs.com/docs/v24.1/transaction-retry-error-reference)
