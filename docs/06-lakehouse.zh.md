# 06 · 真实表快照、演进与时间旅行

## 目标与前置

完成 02、04–05。理解合法文件为何还需要表成员元数据，实测历史行集合、字段身份与混合分区规范。本章运行 **PyIceberg 0.10.0 / 表格式 v2**，使用本地 SQLite catalog 与文件系统。这里的 SQLite 是开发目录，不是分布式事务服务。

## 提交文件集合，不是列举目录

一个 Parquet 文件可以完全合法，却不属于表的任何已提交版本。Iceberg 元数据标识快照，Manifest 描述快照选中的文件，Catalog 标识当前元数据指针。读取目录下所有文件，会绕过这层成员决策。

反例直接在表数据目录写入一个包含 id=999 的合法 Parquet，不提交到表。PyArrow 能成功读取它；朴素地列举所有物理文件并合并 ID，会得到 999。真实 Iceberg 扫描只返回 1–6，因为没有已提交 Manifest 引用该文件。实验保留这个文件，不执行快照过期或删除。

## 从零运行

```sh
pip install -r requirements-iceberg.txt
python lab.py iceberg
python scripts/validate_iceberg.py results/iceberg.json
```

不需要 JVM、Docker、云账户、API Key 或远程 Catalog。输入是六条逐项列明的合成记录，第七条是明确的未提交对照。每次运行创建独占 build/iceberg 目录。`experiments/iceberg_snapshots.py` 分别列出写入批次与字面量预期行集合，验证器独立核对报告约定。证据页可查看完整保存结果。

## 先预测，再运行

| 步骤 | 需要验证的预测 |
| --- | --- |
| 追加三行 | 首个数据快照恰好包含 1、2、3 |
| 再追加两行 | 第二快照包含 1–5，第一快照仍可读取 |
| category 改名 topic，新增可空 quality | 字段 ID 2 保留，旧记录 quality 为 null |
| 给 topic 增加 identity 分区 | 旧文件保留规范 0，只有新文件使用规范 1 |
| 追加 id=6 | 第三个数据快照用演进后 Schema 读取六行 |
| 绕过表提交写入合法 id=999 | 目录合并包含它，Iceberg 成员选择排除它 |

改名更新字段名称，保留字段身份，不重写旧 Parquet 字节。实验读取物理 Parquet 字段元数据：两个旧文件仍叫 `category`，新文件叫 `topic`，但均使用字段 ID 2。Iceberg 当前投影能正确解析改名后的列，旧文件 SHA256 验证元数据操作没有改动它们。

## Schema 提交不等于数据快照

Schema 变化写出新的表元数据版本，但第二个数据快照 ID 保持不变。在本次固定 PyIceberg 读取器中，`scan()` 投影当前表 Schema，`scan(snapshot_id=...)` 选择快照保存的 Schema。因此，Schema-only 提交后，两种调用可以对同一文件成员集合给出不同列名。记录的行与前后 ID 可以直接验证这一点。

这是 PyIceberg 0.10.0 API 的实际行为，不代表每个 SQL 引擎都有相同的时间旅行 Schema 策略。比较结果时要注明读取器版本与投影方式。

## 实际结果与元数据核对

三个数据快照分别包含 **3 / 5 / 6 行**，父子链经过验证。后续提交完成后，历史扫描仍与早先的字面量预期完全相同，规范化行集合哈希保持不变；latest 的哈希不同。哈希包含列名，因此报告明确给出规范化定义。

最终文件计划同时包含分区规范 **0 和 1**。过滤 `topic = 'storage'` 时，可能匹配的旧未分区文件仍是候选，另一个旧文件可由文件统计排除；精确过滤返回 **1、3、6**。计划列出候选文件，不等于测量了实际磁盘 I/O。

新的 Catalog 对象重新加载 SQLite 指针，读到相同最终行。报告还从真实元数据 JSON 核对格式版本、当前 Schema/规范/快照、父 ID 与记录数。公开证据只含这些字段的白名单和合成文件相对路径；完整元数据与 Catalog 留在本地，因为原始位置可能含机器路径。

## 目录不等于表，表也不等于引擎

快照会复用文件，不会每次提交复制全量数据。保留的快照可能仍引用旧文件，按表面年龄删除对象会破坏读取。本实验不做破坏性维护，只验证一个本地库/Catalog/文件组合，不验证目录并发、崩溃原子性、对象存储故障、删除文件跨引擎兼容或生产容量。

HDFS 与对象存储是不同存储路线，Iceberg 是表格式，Parquet 是文件格式，读取器负责规划和执行扫描。本 Profile 使用本地文件，不声称验证 AWS 行为。

## 动手任务

只修改最后一条追加记录的 topic，先预测过滤行集合，再检查文件规范 ID。随后给第二个字段改名，在追加数据前比较当前与固定快照投影。保留旧文件哈希与字面量预期，不要放宽断言去接受原因不明的变化。这些是原创 Lab 练习，不是大学作业解答。

## 2026 阅读拓展：检索的数据血缘

MIT 已公开的 Spring 2026 第 17 讲覆盖 Embedding、RAG 与向量数据库。本 Lab 的关联是工程推理：检索索引构建应记录源快照、Schema、预处理版本与模型版本。实验验证固定快照的数据成员稳定，以及 latest 视图变化，不生成向量、不调用 LLM，也不评测检索质量。

## 自测

**Schema-only 更新产生第四个数据快照吗？** 没有。**为什么物理文件还叫 category？** 字段身份支持无需重写的逻辑改名。**本地 SQLite 能证明分布式 Catalog 安全吗？** 不能。**为什么排除 999？** 它不在已提交 Manifest 中，不是因为 Parquet 行非法。**新分区规范会自动重写旧文件吗？** 本实验中旧规范与旧文件均保留。

## 大学课程导读与原创练习

- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 20 / 2026-04-28 · Cloud DB](https://dsg.csail.mit.edu/6.5830/lectures/lec20.pdf)
- [Apache Iceberg · Schema evolution; Partition evolution; Query the data · PyIceberg API: schema evolution, partition evolution and scans](https://py.iceberg.apache.org/api/)
- [Apache Iceberg · SQL Catalog; Development only · PyIceberg configuration: SQL Catalog / SQLite](https://py.iceberg.apache.org/configuration/#sql-catalog)
- [Apache Iceberg · Snapshots; Schemas; Partition specs; File metadata · Iceberg Table Specification](https://iceberg.apache.org/spec/)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 17 / 2026-04-14 · Embeddings, RAG, and Vector DBs](https://dsg.csail.mit.edu/6.5830/lectures/lec17.pdf)

创建真实快照，按字段身份改名，演进分区规范，对照固定快照读取与目录遍历。

```sh
pip install -r requirements-iceberg.txt
python lab.py iceberg
```

快照行集合 3/5/6，字段 ID 2 改名后保留，文件规范 0/1 共存，旧哈希不变，未提交 id=999 不进入表。

以上是原创 Lab 练习，不是大学课程作业答案。公开阅读不等于注册、学分或评分资格；可检索资源库列出先修与核验日期。

## 原始来源

- [PyIceberg 0.10.0 发行记录](https://github.com/apache/iceberg-python/releases/tag/pyiceberg-0.10.0)
- [PyIceberg API：Schema、分区演进与扫描](https://py.iceberg.apache.org/api/)
- [SQL Catalog / SQLite 开发范围](https://py.iceberg.apache.org/configuration/#sql-catalog)
- [Iceberg 表规范](https://iceberg.apache.org/spec/)
- [MIT Spring 2026 第 20 讲：Cloud DB](https://dsg.csail.mit.edu/6.5830/lectures/lec20.pdf)
- [MIT Spring 2026 第 17 讲：Embedding、RAG 与向量数据库](https://dsg.csail.mit.edu/6.5830/lectures/lec17.pdf)
