# Distributed Data Systems Lab

[English course](https://lynnlee1229.github.io/distributed-data-lab/en/) · [中文课程](https://lynnlee1229.github.io/distributed-data-lab/zh/) · [中文说明](README.zh-CN.md)

Six original chapters organized by concepts and prerequisites: files / blocks / objects and metadata; Parquet layout; HDFS replication; WAL / LSM / MVCC and indexes; cross-range transactions; lakehouse snapshots and evolution. Chapters 02, 03 and 05 have real reproducible profiles. Chapters 01, 04 and 06 are reading / design exercises. No executed Iceberg or cloud claim is made.

The browser Parquet inspector reads local header/footer slices, displays actual metadata and estimates candidate row groups for raw integer bounds. It never uploads a file. This is separate from saved PyArrow engine-read measurements. All public datasets are synthetic. No user documents, logs, credentials or private homepage source are included.

## Reproduce

Python 3.11, JDK 11 (for HDFS), Node 18+ for parser tests. The saved baseline uses macOS arm64 with 16 GiB RAM. PyArrow 20.0.0, HDFS 3.4.2, CockroachDB 24.1.24. The database binary is used only for limited non-production teaching; its upstream license applies. No account, paid key, Docker or cloud resource is needed. The pinned older engine is not a production deployment recommendation.

```sh
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python lab.py parquet
python scripts/bootstrap.py hdfs
python lab.py hdfs
python scripts/bootstrap.py database
python lab.py database
python scripts/index_results.py
python -m unittest discover -s tests -v
node tests/parquet.test.mjs
python scripts/build_site.py
python scripts/check_site.py
python -m http.server 18916 --bind 127.0.0.1 --directory build/site
```

Open http://127.0.0.1:18916/distributed-data-lab/en/. Native runtimes are downloaded from upstream and checksum-verified into ignored build/vendor. On Linux set JAVA_HOME to JDK 11; macOS chooses the installed JDK 11 automatically. Downloads support Linux x86_64/arm64 and macOS arm64. Have at least 8 GiB total memory, about 3 GiB idle for one profile and at least 8 GiB free disk. Profiles are independent and run sequentially; no entire brand stack is required. `python lab.py all` runs all profiles after bootstrap. `--smoke` reduces only Parquet rows and preserves baseline results in results/.

## What the experiments prove

| Profile | Real observation | Boundary |
| --- | --- | --- |
| parquet | Five equal logical layouts; 45 equal-result queries; counted read spans, timing, footer candidates | Requested bytes are reader calls, not physical disk I/O; warm cache |
| hdfs | Four DataNodes, RF=3, thirteen blocks; stop one node, verify digest, restore three live replicas on survivors | One NameNode; one host; no rack/HA or host-failure test |
| database | Three database processes, distinct range leaseholders; cross-range transfer; real 40001 write-skew rejection | One host; no crash atomicity or production capacity benchmark |

The HDFS experiment needs four initial nodes for RF=3 so three survivors can restore full redundancy. Only three initial nodes would be readable but unable to repair to three distinct live replicas after one stops. The database experiment verifies actual writes to distinct serving nodes in KV trace, not merely the number of processes. All raw logs and stores remain ignored and local; sanitized result fields are explicitly authored in each experiment.

## Ownership and safety

All services bind to 127.0.0.1 and are unauthenticated teaching configurations. Do not expose or tunnel them. Database diagnostic / crash reporting is disabled. Ports: HDFS 18920–18921, 19000–19003, 19100–19103, 19200–19203; database 19300–19302 and 19400–19402. A busy port fails before startup. An atomic lock guards profiles; set DDS_RESOURCE_LOCK to a shared lock directory on a machine running other labs. Never remove another run's lock. Owned processes stop in finally; the wrapper terminates only its newly created process group after interruption / timeout. No global daemon, firewall, Docker cleanup or paid service change is performed.

Read [full setup and methods](docs/reproduce.en.md), [validation](VALIDATION.md), per-chapter tasks and self-check answers, and direct primary-source links. CI runs separate Linux jobs and retains generated evidence; those runs are not the laptop baseline. `scripts/build_site.py` exports a file allowlist and creates an independently usable ZIP; build directories, downloaded binaries, private environments and raw logs are excluded. Only this companion is public; the personal homepage source remains private.

HDFS child environments remove inherited Hadoop configuration variables, verify JDK 11, and use per-node PID directories / identities. This is required even for foreground daemons because the upstream shell can use PID files.
