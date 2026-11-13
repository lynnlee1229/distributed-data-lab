# 分布式数据库与存储实验室

[中文课程](https://lynnlee1229.github.io/distributed-data-lab/zh/) · [English](README.md)

六章按概念依赖组织：文件/块/对象与元数据，Parquet 物理布局，HDFS 副本，WAL/LSM/MVCC 与索引，跨范围事务，湖仓快照与演进。02、03、05 有真实实操；01、04、06 是阅读/设计练习，没有 Iceberg 或云服务实测结论。

浏览器检查器只在本地读取 Parquet Header/Footer，显示真实元数据，按原始整数界限估算候选组，不上传文件；它与保存的 PyArrow 实际读取请求测量分开。公开内容全部使用合成数据，不包含用户文档、原始日志、凭据或私有主页源码。

环境与运行命令见 [从零复现](docs/reproduce.zh.md)。固定 Python 3.11、JDK 11、PyArrow 20.0.0、HDFS 3.4.2、CockroachDB 24.1.24。数据库只用于其许可允许的有限非生产教学，不需要账户、付费 Key、Docker 或云资源；固定旧版本不是生产部署建议。

三个 Profile 独立、串行运行：Parquet 对比五种等价布局与 45 次等结果查询；HDFS 四节点 RF=3，停一节点后校验读取与幸存节点上的副本恢复；数据库三个真实进程、不同范围租约，执行跨范围转账并观察 40001 冲突。所有节点共用宿主机，不代表多机扩展性或生产容量。

服务只绑定 127.0.0.1。运行器先检查端口，使用原子资源锁，finally 清理自己的进程；超时只终止新建的本次进程组。共用机器可设置 DDS_RESOURCE_LOCK 指向统一锁。原始日志、数据目录、运行时下载均留在忽略的 build/。公开 ZIP 与静态站按白名单导出。完整结果见 results/，验证见 [VALIDATION.md](VALIDATION.md)。主页源码继续保持私有。
