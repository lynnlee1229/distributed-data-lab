# Reproduce from zero

## Goal and tested baseline

Run each profile independently, inspect the recorded assertions, and keep raw runtime logs local. No cloud service, API key, paid feature or Docker is needed. Tested host: macOS arm64, 16 GiB RAM. The three database nodes and four DataNodes are processes on one host, not separate physical machines.

Python **3.11**, PyArrow **20.0.0**, JDK **11**, HDFS **3.4.2**, CockroachDB **24.1.24**, psycopg2-binary **2.9.10**. This is a pinned teaching baseline, not a recommendation to deploy an older database version in production. Original companion code is MIT; downloaded runtimes retain their upstream licenses and are not bundled in the ZIP.

## Install

```sh
git clone https://github.com/lynnlee1229/distributed-data-lab.git
cd distributed-data-lab
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Install JDK 11 separately and set JAVA_HOME (macOS runner selects the installed JDK 11 automatically). Linux x86_64 and arm64, and macOS arm64 are supported download targets; only macOS arm64 is the saved local measurement environment. CI uses Linux x86_64 separately.

```sh
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

Open `http://127.0.0.1:18916/distributed-data-lab/en/`. Each runtime profile shuts down its owned processes in finally. `python lab.py all` runs profiles sequentially after both runtime downloads. `--smoke` reduces only the Parquet data and saves to build/smoke-parquet.json; baseline evidence is retained. Tests for the browser parser use generated build/parquet files, so run the regular Parquet profile first.

## Resources, ports and ownership

Use a machine with at least 8 GiB total RAM and adequate idle memory; allow about 3 GiB free for a runtime profile, plus existing services. Leave at least 8 GiB free disk for downloads and temporary stores. Hadoop's official archive is about 1 GiB; extraction retains common/HDFS binaries and dependencies. Downloads resume where supported and verify upstream checksums. Stores and raw logs stay in ignored build/.

The runner uses an atomic build/runtime.lock. On a machine shared with other labs, set `DDS_RESOURCE_LOCK` to your common resource-lock directory before invoking lab.py. An occupied lock is an explicit stop; inspect ownership and do not delete another live run's lock. Profiles have a ten-minute limit; the runner terminates only its newly created process group on interruption / timeout.

HDFS binds RPC/UI to 127.0.0.1:18920/18921; DataNode data ports 19000–19003, HTTP 19100–19103, IPC 19200–19203. Database SQL uses 19300–19302, HTTP 19400–19402. The runner preflights all ports. All configurations are unauthenticated teaching configurations restricted to loopback; never expose or tunnel them. Crash reporting and diagnostic reporting are disabled for the database. There is no global firewall change.

## Inspect and modify

- `results/parquet.json`: full logical equality, expected output, per-file metadata and every counted read span / measured repetition.
- `results/hdfs.json`: block placement before/after failure, node states and checksum equality.
- `results/database.json`: actual range placement, trace, executed plan, metrics and both transaction outcomes.
- `scripts/inspect_parquet.py FILE`: inspect a local file with PyArrow; writes JSON to stdout only. The browser inspector reads just header/footer slices and never uploads a selected file.

Change one variable at a time. Predict an invariant before timing. All baseline examples are synthetic. Do not commit your input files, credentials, database stores or raw logs. The site exporter uses an explicit file allowlist and publishes only sanitized results; it does not copy build/ wholesale.

## Interpretation and failure handling

A bind error means another process owns a required port. A runtime-download error leaves a resumable .part file. A failed assertion leaves local logs under build/ and publishes no new success claim. If HDFS cannot reach RF=3, inspect available targets; do not weaken the assertion to call an under-replicated cluster “repaired”. If a database schedule does not produce 40001, inspect returned reads and transaction mode rather than injecting a fake error.

The CI workflow runs Parquet and native integration profiles in separate jobs and uploads generated result artifacts. Its results are independent from the committed laptop baseline. Course chapters 01 and 04 remain reading / reasoning; 02, 03, 05 and 06 have executed profiles. There is no cloud, hotspot capacity or cross-machine benchmark.

HDFS child environments remove inherited Hadoop configuration variables, verify JDK 11, and use per-node PID directories / identities. This is required even for foreground daemons because the upstream shell can use PID files.

## Optional local Iceberg profile

```sh
pip install -r requirements-iceberg.txt
python lab.py iceberg
python scripts/validate_iceberg.py results/iceberg.json
python scripts/index_results.py
python scripts/verify_resources.py
```

Fixed PyIceberg 0.10.0 and SQLAlchemy 2.0.44 use the same PyArrow 20.0.0 baseline. No JVM, Docker, cloud service, API key or network listener is required. Input is six enumerated synthetic rows plus a deliberately uncommitted valid Parquet row. The profile is tiny; it does not estimate capacity. `all` retains the original three-profile behavior; the optional profile is run separately.

Every Iceberg run creates a unique build/iceberg directory, so rerunning never purges a previous table's history. The report's local_artifact_directory identifies its own catalog/warehouse. Raw metadata has local locations and stays ignored; only selected schema/spec/snapshot fields, file hashes, literal rowsets and relative synthetic references are exported. No snapshot expiration, table purge or file deletion is run. SQLite catalog behavior is development scope, not distributed-catalog safety.

Check snapshots with 3/5/6 rows, field ID 2 before/after rename, mixed spec IDs 0/1, unchanged old file SHA256, the persisted catalog pointer and historical rowset hashes. The negative control must show id=999 in raw file enumeration but absent from Iceberg. A separate validator rejects corrupted evidence; the engine runner itself compares actual reads against literal rowset oracles.

The resource inventory maps six original exercises to verified CMU/MIT lectures and official tutorials. `verify_resources.py` validates it offline; `--live` performs bounded public URL prefix reads. Reading public slides requires no course enrollment in our checks, but course registration, grades, credit and fees remain separate. Do not publish official course solutions. The 2026 retrieval-index extension is reading and a lineage discussion, not a model or RAG-quality experiment.
