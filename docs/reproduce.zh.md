# 从零复现

## 目标与实测基线

独立启动各 Profile，检查结果断言，并把原始日志留在本地。不需要云服务、API Key、付费特性或 Docker。已测环境为 macOS arm64、16 GiB 内存。三个数据库节点、四个 DataNode 都是同一宿主上的进程，不是多台物理机器。

固定版本：Python **3.11**、PyArrow **20.0.0**、JDK **11**、HDFS **3.4.2**、CockroachDB **24.1.24**、psycopg2-binary **2.9.10**。这是教学基线，不建议把旧版数据库直接用于生产。配套原创代码采用 MIT；运行时保留上游许可，不打包进 ZIP。

## 安装与运行

```sh
git clone https://github.com/lynnlee1229/distributed-data-lab.git
cd distributed-data-lab
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python lab.py parquet
python scripts/bootstrap.py hdfs
python lab.py hdfs
python scripts/bootstrap.py database
python lab.py database
python -m unittest discover -s tests -v
node tests/parquet.test.mjs
python scripts/build_site.py
python scripts/check_site.py
python -m http.server 18916 --bind 127.0.0.1 --directory build/site
```

另行安装 JDK 11 并设置 JAVA_HOME；macOS 会自动选择已安装的 JDK 11。下载支持 Linux x86_64/arm64 与 macOS arm64；保存的本地测量来自 macOS arm64，CI 的 Linux 记录单列。

打开 `http://127.0.0.1:18916/distributed-data-lab/zh/`。各 Profile 在 finally 中停止自己启动的进程。两种运行时下载完成后，`python lab.py all` 按顺序执行。`--smoke` 只缩小 Parquet 数据并写入 build/smoke-parquet.json，不覆盖正式基线。浏览器解析测试依赖 build/parquet 文件，需先运行普通 Parquet Profile。

## 资源、端口与归属

使用至少 8 GiB 总内存、留有足够空闲的机器；除既有服务外，为单个 Profile 留约 3 GiB 可用内存。磁盘至少留 8 GiB。Hadoop 官方压缩包约 1 GiB，只提取 common/HDFS 相关内容。下载支持服务端允许的断点续传并校验上游摘要。数据目录与原始日志只留在已忽略的 build/。

运行器用原子目录 build/runtime.lock 互斥。多 Lab 共用机器时，把 `DDS_RESOURCE_LOCK` 设置为统一资源锁目录，再运行 lab.py。锁被占用就停止，检查所有者，不删除别人仍使用的锁。每个 Profile 限十分钟；中断或超时只终止本次新建的进程组。

HDFS RPC/UI 绑定 127.0.0.1:18920/18921；DataNode 数据端口 19000–19003、HTTP 19100–19103、IPC 19200–19203。数据库 SQL 19300–19302、HTTP 19400–19402。启动前逐一检查端口。这里采用无认证教学配置，只限回环，不能暴露或转发到公网。数据库崩溃上报与诊断上报关闭，不修改全局防火墙。

## 检查与修改

- `results/parquet.json`：逻辑数据相同、预期输出、逐文件元数据、所有读取区间与正式重复测量。
- `results/hdfs.json`：故障前后块位置、节点状态与摘要一致性。
- `results/database.json`：真实范围放置、Trace、已执行计划、指标及双方事务结果。
- `scripts/inspect_parquet.py FILE`：用 PyArrow 检查本地文件，只向 stdout 输出 JSON。浏览器检查器只读 Header/Footer 切片，不上传所选文件。

一次只改一个变量，先写正确性不变量，再比较耗时。基线全部是合成数据。不要提交自己的输入文件、凭据、数据库数据目录或原始日志。站点导出按文件白名单执行，只发布经检查的结果，不会整体复制 build/。

## 结果边界与失败处理

绑定失败说明端口已被其他进程占用；下载失败保留可续传 .part 文件。断言失败把本地日志留在 build/，不发布新的成功结论。HDFS 无法达到 RF=3 时先检查可用目标，不能放宽断言把副本不足称为已恢复。数据库没出现 40001 时应检查返回给客户端的读取与事务模式，不人为注入错误冒充冲突。

CI 在独立 Job 中运行 Parquet 与本机原生集成 Profile，上传生成结果，与已提交的笔记本基线分开。01、04、06 为阅读/推理；02、03、05 有真实实操。没有执行 Iceberg、云服务、热点容量或跨机器扩展性基准。

HDFS 子进程会清除继承的 Hadoop 配置变量、核验 JDK 11，并使用各节点独占的 PID 目录与标识；即使前台运行，上游 shell 也可能使用 PID 文件。
