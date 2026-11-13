# 04 · WAL、LSM、MVCC 与索引代价

## 目标与前置

完成 01–03，理解主键与事务。区分恢复、布局、版本可见性和分布式一致。本章是阅读与推理桥梁，不声称测量了 Compaction 或崩溃恢复。

## 四种机制，四个问题

预写日志在变更持久化应用到其他结构之前记录变化，可用于恢复，但保证取决于实际同步策略与故障模型。LSM 引擎先在内存收集写入，刷新有序表，再后台合并。把即时更新改成后台归并，会在写放大、读放大与空间放大之间取舍。“顺序写”不等于所有 LSM 工作负载都很便宜。

MVCC 保留多个版本，让读者选择一致的可见性时点；旧版本需要保留与回收规则。快照保护视图，并不意味着所有并发“读后修改”都能安全提交，可串行化还需要额外冲突控制。

复制协议解决不同节点副本的一致。Raft 日志与引擎 WAL 虽然都叫日志，职责并不相同。多数派接受命令，与事务决定所有参与者的更新，是不同协议层。它们也不等价于把文件写入 HDFS。

## 索引键也会成为放置键

主索引保存行的编码键值表示。二级索引引入额外键，通常位于有序键空间的其他位置，因此更新一行也可能跨越多个 Range。Range 是连续键区间，每个区间都可复制。Leaseholder 承担相应请求职责，其他副本维护范围。更多范围不等于无限独立容量：一个热键在某时刻仍只属于一个范围。

下一实验使用真实 CockroachDB 24.1.24 基线，涉及 Pebble、MVCC 与复制范围。证据检查范围放置与事务结果，不检查 Pebble SSTable，也不证明 fsync 行为。

## 数据与代码

阅读 `experiments/distributed_transactions.py` 的 accounts 表。三个主键刻意落在 1000、2000 两个分界形成的不同区间。验证事务正确性只需三行，大数据反而会掩盖执行顺序。

```sql
CREATE TABLE accounts (
  id INT PRIMARY KEY,
  balance INT NOT NULL CHECK (balance >= 0)
);
ALTER TABLE accounts SPLIT AT VALUES (1000), (2000);
SHOW RANGES FROM TABLE accounts WITH DETAILS;
```

## 动手任务与预期结果

画出主键与一个假设的 balance 二级索引条目，列出转账时会改变的键。区分“行在本地持久化”“范围复制了命令”“事务提交”“某个快照可见新版本”四句话；它们各需不同证据。这是纸面练习，实测结论只来自第 05 章。

## 自测

**MVCC 会消除写冲突吗？** 不会。**加二级索引没有写代价吗？** 不是，可能增加键与协调工作。**Compaction 能马上删除所有旧版本吗？** 不能，活跃读者与保留规则可能仍需它们。**单靠范围切分能解决单热键吗？** 不能，该键流量仍然集中。

## 大学课程导读与原创练习

- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #05 · Database Storage II](https://15445.courses.cs.cmu.edu/fall2025/slides/05-storage2.pdf)
- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #20 · Multi-Version Concurrency Control](https://15445.courses.cs.cmu.edu/fall2025/slides/20-multiversioning.pdf)
- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #21 · Database Logging](https://15445.courses.cs.cmu.edu/fall2025/slides/21-logging.pdf)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 12 / 2026-03-19 · Optimistic Concurrency Control, Snapshot Isolation](https://dsg.csail.mit.edu/6.5830/lectures/lec12.pdf)

阅读已执行计划中的主索引路径与版本/冲突调度，另列出验证 WAL 持久性或 LSM 合并所需证据。

```sh
python scripts/bootstrap.py database
python lab.py database
```

计划标明 accounts_pkey；可串行化冲突不是 WAL fsync 或 Compaction 测量，后两者仍属阅读。

以上是原创 Lab 练习，不是大学课程作业答案。公开阅读不等于注册、学分或评分资格；可检索资源库列出先修与核验日期。

## 原始来源

- [CockroachDB 存储层](https://www.cockroachlabs.com/docs/v24.1/architecture/storage-layer)
- [CockroachDB 复制层](https://www.cockroachlabs.com/docs/v24.1/architecture/replication-layer)
- [CockroachDB 事务层](https://www.cockroachlabs.com/docs/v24.1/architecture/transaction-layer)
- [Pebble 项目与文档](https://github.com/cockroachdb/pebble)
