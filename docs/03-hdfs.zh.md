# 03 · HDFS：定位字节与恢复副本

## 目标与前置

完成 01–02，理解进程与复制。能够追踪客户端读取，检查真实块分布，区分“读成功”与“冗余恢复”。

## 元数据路径与数据路径

客户端向 NameNode 查询块位置，然后从 DataNode 读数据，并不经由 NameNode 转发所有文件字节。复制让每个块具有多个放置位置，校验和辅助发现损坏。文件可读不代表副本数达标：一份幸存副本就可能完成读取，但冗余已经不足。

DataNode 故障后停止心跳，检测需要时间，因此早期读取可能先尝试已停止的地址，再重试其他副本。检测后，NameNode 才安排在合格目标上补副本。恢复同时需要幸存源与尚未持有该块的可用目标。配置了目标副本数，不保证集群一定有足够节点满足它。

## 数据与可执行代码

`experiments/hdfs_recovery.py` 运行 HDFS 3.4.2：一个 NameNode、四个独立 DataNode 进程和数据目录，全部绑定本机回环。副本数为 3。合成文件大小为 12 MiB 加 173 字节，块大小 1 MiB，共十三块。小块用于直观看到分布，不是生产调参建议。

```sh
python scripts/bootstrap.py hdfs
python lab.py hdfs
```

实验只格式化自己忽略的 build 目录，等待四节点在线后写文件，采集 `fsck -files -blocks -locations`，验证每块有三个活副本。接着用 SIGTERM 停止自己的一个 DataNode；在它保持停止时读取并比对 SHA256，观察 3 live / 1 dead，再轮询每块是否在幸存节点恢复三个活副本。不会通过重启故障节点伪装完成补副本。

## 实际结果与解释

证据页保存故障前后放置位置、校验和与状态。对比块位置列表：原来位于被停止传输端口上的块，现在应补到另外三个节点。故障前和故障后两次读取必须得到相同摘要。

四节点很关键。如果一开始只有三节点、RF=3，停一台后只剩两个合格存活节点；可以继续读取，却不能凭空恢复三个不同节点上的活副本，必须等节点返回或加入新节点。本实验明确提供额外目标。四个进程共用宿主机和故障域，宿主故障会同时影响它们。

实验把心跳缩短到 1 秒，recheck 设为 1000 ms，副本检查设为 1 秒；默认生产超时不适合短课。轮询可能错过短暂的副本不足区间。死亡检测观测时间包含一次故障后读取；恢复计时是观察到完成的上界，不是精确调度耗时。

## 小文件与边界

小文件不等于自动占满一个块的字节容量，但每个文件和块仍需命名空间、块映射等元数据。大量小文件会增加 NameNode 和客户端负担。合并文件还须考虑表快照与读者，盲删旧文件可能破坏仍被引用的版本。这里只有单 NameNode，没有 HA 或机架策略实测。

## 动手任务

先根据文件长度计算块数，再看 fsck。将 RF 改成 2、保留四节点，预测目标选择空间。拓展时可只启三节点、RF=3，并相应修改就绪门槛；诚实记录“可读但副本不足”，不要断言恢复。

## 自测

**摘要相同就证明副本恢复吗？** 不能，还要检查活副本位置。**增加 NameNode 就等于增加文件数据副本吗？** 不是，命名空间可用性与 DataNode 数据复制是两个问题。**四进程是四个独立宿主故障域吗？** 不是。

## 大学课程导读与原创练习

- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 15 / 2026-04-07 · Distributed Databases](https://dsg.csail.mit.edu/6.5830/lectures/lec15.pdf)
- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #23 · Distributed Database Systems I](https://15445.courses.cs.cmu.edu/fall2025/slides/23-distributed1.pdf)
- [Apache Hadoop · NameNode and DataNodes; Data Replication; Robustness · HDFS Architecture 3.4.2](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [Google Research / SOSP 2003 · 2003 classic; architecture and fault-tolerance sections · The Google File System](https://research.google/pubs/the-google-file-system/)

计算块数，停止一个 DataNode，分别验证可读与冗余恢复。

```sh
python scripts/bootstrap.py hdfs
python lab.py hdfs
```

十三块，四节点起步 RF=3；停一节点后每块三个活副本，待恢复/副本不足计数为零。

以上是原创 Lab 练习，不是大学课程作业答案。公开阅读不等于注册、学分或评分资格；可检索资源库列出先修与核验日期。

## 原始来源

- [HDFS 3.4.2 架构](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html)
- [HDFS 3.4.2 命令](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/HDFSCommands.html)
- [HDFS 3.4.2 默认配置](https://hadoop.apache.org/docs/r3.4.2/hadoop-project-dist/hadoop-hdfs/hdfs-default.xml)
