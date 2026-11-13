# 02 · Parquet：先理解布局，再调参数

## 目标与前置

完成 01，理解行、列和整数条件。能够解释 Row Group，检查编码与压缩，并测量读取器真正请求了哪些字节。

## 先横向分组，再纵向分列

一个 Row Group 包含一组行；组内每个叶子列对应一个 Column Chunk，Chunk 再分为 Page。字典编码把重复值替换为编号，游程编码表示连续重复，压缩再转换已编码的页字节。它们是不同决策。低基数标签适合字典，不代表随机载荷也适合。

Footer 让读取器不用解码每一行就能定位列块。若某组 id 的整数范围为 [0,4095]，它不可能满足 [32000,33023]。若范围是 [0,131071]，即使实际没有匹配行，也不能只凭这两个界限排除它。统计提供安全排除条件，不直接提供查询答案。

按键排序会收紧该键的 min/max 区间。小组裁剪更精细，也增加元数据与调度工作；大组可能利于顺序读和压缩，却带入更多无关行。不存在适合所有查询的唯一组大小。

## 数据与可执行代码

`experiments/parquet_layout.py` 以种子 9162026 生成 131,072 行。Schema 包含整数 id/value、32 类 bucket 和确定性 SHA256 文本载荷。五个文件对比排序/打乱、每组 4,096/32,768 行目标以及 ZSTD/Snappy。只对 bucket 使用字典编码。查询前，每个文件都完整解码、按 id 排序，并与同一逻辑表逐项比较。

```sh
python lab.py parquet
python scripts/inspect_parquet.py build/parquet/sorted-4096-zstd.parquet
```

三种模式返回完全相同且有序的 id/value：全列读取并下推过滤；只读所需列并下推过滤；只读所需列、取消下推，再精确过滤。最后一种是扫描所有组的对照。每种模式保留一次预热和三次交替顺序的正式测量。

## 实际结果与解释

证据页保留全部 45 次正式查询。已保存的 4,096 行 ZSTD 文件中，排序布局保留 2/32 个候选组，打乱布局保留 32/32；精确结果为 1,024 行。列选择还会去掉 payload 的请求。报告分开记录候选压缩列块字节估算和引擎实际读取请求；元数据可能重复读取，命中缓存也算请求，这不是物理磁盘或网络计数。

计时包含读取、解码、精确过滤与结果排序，不包含文件生成和结果验证。这是热缓存笔记本观察。少请求字节不保证小查询一定更快，固定开销和缓存同样影响结果。

## 动手任务

把条件改成完全落在一个有序组内，再改成跨组边界；先预测候选数，再运行。把排序键改成 bucket，它还能帮助 id 条件吗？用浏览器检查器打开合成文件，选择列并比较 min/max 条带。检查器的估算不代表已经执行 SQL 查询。

## 自测

**只选择少数列，仍可能读取过滤列吗？** 会，除非元数据已经解决条件，否则仍需列值。**有压缩就不用裁剪吗？** 不是，跳过块与解压块解决不同成本。**没有统计能否证明排除？** 不能，必须保留为候选。

## 大学课程导读与原创练习

- [Carnegie Mellon University 15-445/645 · Fall 2025 · Lecture #06 · Storage Models & Compression](https://15445.courses.cs.cmu.edu/fall2025/slides/06-storage3.pdf)
- [Massachusetts Institute of Technology 6.5830/6.5831 · Spring 2026 · Lecture 10 / 2026-03-10 · OLAP & Column Stores](https://dsg.csail.mit.edu/6.5830/lectures/lec10.pdf)
- [Apache Parquet · File metadata and page headers · Parquet metadata](https://parquet.apache.org/docs/file-format/metadata/)

先预测候选组，再比较真实读取区间；在自己的副本中修改一个过滤边界。

```sh
python lab.py parquet
```

45 次查询均与源数据 oracle 相同；4096 有序布局候选 2/32，打乱为 32/32。

以上是原创 Lab 练习，不是大学课程作业答案。公开阅读不等于注册、学分或评分资格；可检索资源库列出先修与核验日期。

## 原始来源

- [Parquet 列块](https://parquet.apache.org/docs/file-format/data-pages/columnchunks/)
- [Parquet 编码](https://parquet.apache.org/docs/file-format/data-pages/encodings/)
- [Parquet 元数据](https://parquet.apache.org/docs/file-format/metadata/)
- [PyArrow 20 读取 API](https://arrow.apache.org/docs/20.0/python/generated/pyarrow.parquet.read_table.html)
