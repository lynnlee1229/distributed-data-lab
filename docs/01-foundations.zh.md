# 01 · 名称、字节与元数据的权威

## 目标与前置

从这一章开始。只需理解字节与目录。学完后，能够把一个系统放在正确的层次，并说明谁负责记录数据的位置。

## 名称不等于内容

文件提供字节序列、路径和文件系统操作。分布式文件系统把字节序列切成块，保存“文件名 → 块 → 副本位置”的映射。对象存储通过 API 提供键与对象；对象键写得像目录，也不代表它具有文件系统的重命名语义。改键与文件重命名可能需要不同的操作。

元数据也是数据，关键在于它对什么有决定权。Parquet Footer 描述单个文件的 Schema 与布局；NameNode 记录命名空间与块位置；表目录可以指向已经提交的表元数据。三者不能直接互相替代。

## 两条路线，不同约定

| 层次 | 分析型文件路线 | 事务型键值路线 |
| --- | --- | --- |
| API / 执行 | SQL 引擎规划扫描 | SQL 网关规划读写 |
| 逻辑组织 | Iceberg 可追踪表快照 | 数据库索引把行映射到键范围 |
| 本地表示 | Parquet 保存列块 | LSM 引擎保存 MVCC 版本 |
| 持久化 / 放置 | 本地文件、HDFS 或对象存储 | 数据库节点上的复制范围 |

这是职责示例，不是所有系统必须经过的部署链路。Parquet 可以单独存于本地磁盘；Iceberg 可以引用对象存储上的 Parquet，无需 HDFS；CockroachDB 的正常事务存储也不经过 HDFS 或 Parquet。HDFS 与 S3 是存储系统，Parquet 是文件格式，Iceberg 是表格式，查询引擎负责执行，分布式数据库还要负责事务协调与数据放置。

## 数据与代码

所有可执行案例只使用合成字节或固定种子的行。打开 `experiments/parquet_layout.py` 找到 Schema。分别画出 Footer、块位置映射、快照引用、主索引键范围四条元数据记录，为它们选择不同标识。

## 动手任务

针对“查找 id 在 32000 到 33023 之间的行”，写出决策顺序：如涉及表则选择已提交版本；选择文件；读取 Footer；裁剪 Row Group；读取所需列块；解码；执行精确行过滤。标出直接读取独立文件时不存在的步骤。

## 结果与解释

实测从第 02 章开始。本章是职责辨析练习，没有存储基准。正确答案不会给独立 Parquet 读取凭空加上目录或 HDFS。Footer 统计可以排除不可能匹配的组，却不能提供整张表的原子提交。

## 自测

**一个合法 Parquet 文件可能属于发布了一半的表吗？** 可以。单文件合法，不代表已经确定表提交所包含的完整文件集合。**Row Group 是 HDFS Block 吗？** 不是。前者是格式分组，后者是存储分配与复制单位，两者边界不一定对齐。

## 大学课程导读与原创练习

- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #03 · Database Storage I](https://15445.courses.cs.cmu.edu/fall2025/slides/03-storage1.pdf)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 4 / 2026-02-12 · Intro to DB Internals](https://dsg.csail.mit.edu/6.5830/lectures/lec4.pdf)
- [Apache Parquet · File metadata and page headers · Parquet metadata](https://parquet.apache.org/docs/file-format/metadata/)

检查真实 Footer，找出行/列块信息，解释它为什么不知道副本数与表提交。

```sh
python lab.py parquet
python scripts/inspect_parquet.py build/parquet/sorted-4096-zstd.parquet
```

组行数合计为 131072、Schema 四列；存储/表权威是推理题，不能从组数推导副本数。

以上是原创 Lab 练习，不是大学课程作业答案。公开阅读不等于注册、学分或评分资格；可检索资源库列出先修与核验日期。

## 原始来源

- [Parquet 概念](https://parquet.apache.org/docs/concepts/)
- [HDFS 3.4.2 架构](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [S3 对象与键](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingObjects.html)
- [Iceberg 规范](https://iceberg.apache.org/spec/)
