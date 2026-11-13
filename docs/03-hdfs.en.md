# 03 · HDFS: locating bytes and restoring replicas

## Goal and prerequisites

Complete 01–02. Know processes and replication. Trace a client read, inspect real block placement and distinguish successful reads from restored redundancy.

## The metadata path and the data path

A client asks the NameNode for block locations, then reads from DataNodes. It does not fetch all file bytes through the NameNode. Replication creates multiple placements of each block; checksums help detect corruption. A readable file is not necessarily fully replicated: one surviving copy can permit a read while redundancy is below target.

A failed DataNode stops sending heartbeats. Detection is delayed, so an early read can first contact a dead address and retry another replica. After detection, the NameNode schedules new replicas on eligible targets. It needs both a surviving source and an available target that does not already hold that block. Desired replication is not a guarantee that the cluster has enough eligible nodes.

## Data and executable code

`experiments/hdfs_recovery.py` runs HDFS 3.4.2 with one NameNode and four independent DataNode processes/directories, all bound to loopback. Replication factor is 3. The synthetic file is 12 MiB plus 173 bytes, with 1 MiB blocks: thirteen blocks. A small block size makes placement visible; it is not a production tuning recommendation.

```sh
python scripts/bootstrap.py hdfs
python lab.py hdfs
```

The experiment formats only its ignored build directory, waits for four live nodes, writes the file, captures `fsck -files -blocks -locations`, and verifies three live replicas per block. It stops one owned DataNode with SIGTERM, reads and checks SHA256 while that process remains stopped, observes 3 live / 1 dead nodes, then polls for three live replicas of every block on surviving nodes. It never fabricates a repaired replica by restarting the failed node.

## Actual results and interpretation

The evidence page records before/after placement, checksums and observed states. Compare the block-location lists: any block formerly on the stopped transfer port must now have a replacement on the other three nodes. Before and both post-stop reads must share a digest.

Four nodes matter. With RF=3 and only three initial nodes, stopping one leaves only two eligible survivors; the cluster can remain readable but cannot restore three distinct live replicas until a node returns or another joins. This experiment deliberately provides the extra target. All nodes share one host and failure domain; a host crash defeats this arrangement.

The lab shortens heartbeat to 1 second, recheck to 1000 ms and replication check to 1 second. A default production timeout would obscure a short lesson. Polling can miss the brief under-replicated interval. The detection observation includes a post-stop read; repair timing is an upper observation bound, not scheduler latency.

## Small files and limits

One small file does not consume a full block's bytes automatically, but every file and block still adds namespace and block metadata. Many tiny files can burden the NameNode and increase client overhead. Compaction should consider table snapshots and readers; deleting old files blindly can break referenced versions. This lab has one NameNode, with no HA or rack policy test.

## Hands-on task

Count blocks from file length before reading fsck. Change RF to 2 with four nodes and predict target freedom. As a separate extension, start only three nodes at RF=3, adjust the readiness gate, and record “readable but under-replicated” rather than asserting restoration.

## Self-check

**Does a matching digest prove redundancy is restored?** No; inspect live placement too. **Does a second NameNode replica store the file payload?** Namespace availability and DataNode replicas are separate. **Are these four processes four independent host failures?** No.

## Guided university reading and original exercise

- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 15 / 2026-04-07 · Distributed Databases](https://dsg.csail.mit.edu/6.5830/lectures/lec15.pdf)
- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #23 · Distributed Database Systems I](https://15445.courses.cs.cmu.edu/fall2025/slides/23-distributed1.pdf)
- [Apache Hadoop · NameNode and DataNodes; Data Replication; Robustness · HDFS Architecture 3.4.2](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [Google Research / SOSP 2003 · 2003 classic; architecture and fault-tolerance sections · The Google File System](https://research.google/pubs/the-google-file-system/)

Count blocks, stop one DataNode and verify reading and restored redundancy separately.

```sh
python scripts/bootstrap.py hdfs
python lab.py hdfs
```

Thirteen blocks; RF=3 on four starting nodes; after one stops, three live replicas per block and zero pending/under-replicated counters.

These are original Lab exercises, not the universities’ assignment solutions. Public reading access does not grant enrollment, credit or grading. See the searchable resource library for prerequisites and verification dates.

## Original sources

- [HDFS 3.4.2 architecture](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [HDFS 3.4.2 commands](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html)
- [HDFS 3.4.2 configuration defaults](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/hdfs-default.xml)
