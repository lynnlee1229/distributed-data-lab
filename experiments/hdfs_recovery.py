"""Four real HDFS DataNodes, RF=3, one controlled stop and repair on spare targets."""

import hashlib, json, os, random, re, shutil, socket, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTS = (
    [18920, 18921]
    + list(range(19000, 19004))
    + list(range(19100, 19104))
    + list(range(19200, 19204))
)


def run(out=None):
    home = ROOT / "build/vendor/hadoop-3.4.2"
    assert (home / "bin/hdfs").exists(), "Run bootstrap.py hdfs first"
    work = ROOT / "build/hdfs"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    procs = []
    handles = []
    for port in PORTS:
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))
    java = os.environ.get("DDS_JAVA_HOME")
    if not java and __import__("platform").system() == "Darwin":
        java = subprocess.check_output(
            ["/usr/libexec/java_home", "-v", "11"], text=True
        ).strip()
    java = java or os.environ.get("JAVA_HOME")
    assert java, "Set JAVA_HOME to JDK 11"
    java_version = subprocess.check_output(
        [str(Path(java) / "bin/java"), "-version"], stderr=subprocess.STDOUT, text=True
    ).splitlines()[0]
    assert re.search(r"version \"11[.]", java_version), (
        "This profile requires JDK 11: " + java_version
    )

    def config(name, extra):
        conf = work / name
        conf.mkdir()
        (conf / "pids").mkdir()
        props = {
            "fs.defaultFS": "hdfs://127.0.0.1:18920",
            "hadoop.tmp.dir": str(work / "tmp"),
            "hadoop.security.authentication": "simple",
            "dfs.namenode.rpc-address": "127.0.0.1:18920",
            "dfs.namenode.http-address": "127.0.0.1:18921",
            "dfs.namenode.name.dir": str(work / "name"),
            "dfs.replication": "3",
            "dfs.blocksize": "1048576",
            "dfs.heartbeat.interval": "1",
            "dfs.namenode.heartbeat.recheck-interval": "1000",
            "dfs.namenode.replication.interval": "1",
            "dfs.namenode.safemode.min.datanodes": "4",
            "dfs.permissions.enabled": "false",
            "dfs.namenode.datanode.registration.ip-hostname-check": "false",
            **extra,
        }
        xml = (
            "<configuration>"
            + "".join(
                f"<property><name>{k}</name><value>{v}</value></property>"
                for k, v in props.items()
            )
            + "</configuration>"
        )
        for file in ["core-site.xml", "hdfs-site.xml"]:
            (conf / file).write_text(xml)
        (conf / "hadoop-env.sh").write_text("")
        shutil.copy2(home / "etc/hadoop/log4j.properties", conf / "log4j.properties")
        clean = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("HADOOP_", "HDFS_", "YARN_", "MAPRED_"))
            and k != "CLASSPATH"
        }
        return {
            **clean,
            "HADOOP_YARN_HOME": str(home),
            "HADOOP_MAPRED_HOME": str(home),
            "HADOOP_COMMON_HOME": str(home),
            "HADOOP_HDFS_HOME": str(home),
            "JAVA_HOME": java,
            "HADOOP_HOME": str(home),
            "HADOOP_CONF_DIR": str(conf),
            "HADOOP_LOG_DIR": str(work / "logs"),
            "HADOOP_PID_DIR": str(conf / "pids"),
            "HADOOP_IDENT_STRING": "dds-" + name,
            "HADOOP_HEAPSIZE_MAX": "256",
            "HADOOP_OPTS": "-Djava.net.preferIPv4Stack=true -Duser.name=lab",
        }

    env = config("nnconf", {})

    def cli(*args, timeout=60):
        return subprocess.check_output(
            [str(home / "bin/hdfs"), *args],
            env=env,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )

    def spawn(role, e):
        h = open(work / (role + str(len(procs)) + ".log"), "wb")
        handles.append(h)
        p = subprocess.Popen([str(home / "bin/hdfs"), role], env=e, stdout=h, stderr=h)
        procs.append(p)
        return p

    def state():
        with urllib.request.urlopen(
            "http://127.0.0.1:18921/jmx?qry=Hadoop:service=NameNode,name=FSNamesystem*",
            timeout=3,
        ) as r:
            beans = json.load(r)["beans"]
        wanted = [
            "NumLiveDataNodes",
            "NumDeadDataNodes",
            "BlocksTotal",
            "UnderReplicatedBlocks",
            "MissingBlocks",
            "PendingReplicationBlocks",
            "PendingReconstructionBlocks",
            "LowRedundancyBlocks",
        ]
        return {k: b[k] for b in beans for k in wanted if k in b}

    def wait(test, timeout=150):
        end = time.monotonic() + timeout
        last = None
        while time.monotonic() < end:
            try:
                last = test()
                if last:
                    return last
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            time.sleep(1)
        raise RuntimeError("Timed out waiting for HDFS: " + str(last))

    def fsck():
        raw = cli("fsck", "/lab/data.bin", "-files", "-blocks", "-locations").decode()
        raw = re.sub(r"Connecting to namenode via .*\n", "", raw)
        raw = re.sub(
            r"FSCK started by .*? for path", "FSCK started by lab for path", raw
        )
        blocks = []
        for line in raw.splitlines():
            if "Live_repl=" in line:
                blocks.append(
                    {
                        "block": re.search(r"(blk_-?\d+_\d+)", line).group(1),
                        "live_replicas": int(
                            re.search(r"Live_repl=(\d+)", line).group(1)
                        ),
                        "locations": re.findall(r"127\.0\.0\.1:(1900[0-3])", line),
                    }
                )
        return {"blocks": blocks, "text": raw}

    try:
        with open(work / "format.log", "wb") as f:
            subprocess.run(
                [
                    str(home / "bin/hdfs"),
                    "namenode",
                    "-format",
                    "-force",
                    "-nonInteractive",
                ],
                env=env,
                stdout=f,
                stderr=f,
                check=True,
                timeout=60,
            )
        spawn("namenode", env)
        wait(lambda: state())
        dns = []
        for i in range(4):
            e = config(
                "dnconf" + str(i),
                {
                    "dfs.datanode.data.dir": str(work / f"data{i}"),
                    "dfs.datanode.address": f"127.0.0.1:{19000+i}",
                    "dfs.datanode.http.address": f"127.0.0.1:{19100+i}",
                    "dfs.datanode.ipc.address": f"127.0.0.1:{19200+i}",
                    "dfs.datanode.hostname": "127.0.0.1",
                },
            )
            e["HADOOP_HEAPSIZE_MAX"] = "128"
            dns.append(spawn("datanode", e))

        def ready():
            if any(p.poll() is not None for p in procs):
                raise RuntimeError(
                    "An owned HDFS process exited; inspect build/hdfs logs"
                )
            return state().get("NumLiveDataNodes") == 4

        wait(ready)
        cli("dfsadmin", "-safemode", "wait")
        data = random.Random(9162026).randbytes(12 * 1024 * 1024 + 173)
        local = work / "data.bin"
        local.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        cli("dfs", "-mkdir", "-p", "/lab")
        cli("dfs", "-put", str(local), "/lab/data.bin")
        before = fsck()
        assert len(before["blocks"]) == 13 and all(
            b["live_replicas"] == 3 for b in before["blocks"]
        )
        before_state = state()
        victim = int(before["blocks"][0]["locations"][0]) - 19000
        start = time.monotonic()
        dns[victim].terminate()
        dns[victim].wait(timeout=15)
        # Read while a real DataNode process is stopped. HDFS client retries surviving replicas.
        read_after_stop = hashlib.sha256(
            cli("dfs", "-cat", "/lab/data.bin", timeout=120)
        ).hexdigest()
        assert read_after_stop == digest
        detected = wait(
            lambda: (
                s
                if (s := state()).get("NumLiveDataNodes") == 3
                and s.get("NumDeadDataNodes") == 1
                else False
            )
        )
        detected_ms = (time.monotonic() - start) * 1000

        def repaired():
            f = fsck()
            return (
                f
                if len(f["blocks"]) == 13
                and all(
                    b["live_replicas"] == 3
                    and str(19000 + victim) not in b["locations"]
                    for b in f["blocks"]
                )
                else False
            )

        after = wait(repaired)
        after_state = wait(
            lambda: (
                s
                if (s := state()).get("NumLiveDataNodes") == 3
                and s.get("UnderReplicatedBlocks", s.get("LowRedundancyBlocks", -1))
                == 0
                and s.get(
                    "PendingReplicationBlocks", s.get("PendingReconstructionBlocks", -1)
                )
                == 0
                else False
            )
        )
        after = fsck()
        assert all(
            b["live_replicas"] == 3 and str(19000 + victim) not in b["locations"]
            for b in after["blocks"]
        )
        repaired_ms = (time.monotonic() - start) * 1000
        digest2 = hashlib.sha256(cli("dfs", "-cat", "/lab/data.bin")).hexdigest()
        assert digest2 == digest
        result = {
            "experiment": "hdfs",
            "executed_at": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat(),
            "version": "3.4.2",
            "java_major": 11,
            "java_version": java_version,
            "seed": 9162026,
            "topology": {
                "namenodes": 1,
                "datanodes_before": 4,
                "datanodes_after": 3,
                "replication_factor": 3,
                "block_bytes": 1048576,
                "single_host": True,
                "bind": "127.0.0.1",
                "heap_mib": {"namenode": 256, "each_datanode": 128},
            },
            "data_bytes": len(data),
            "sha256": digest,
            "after_stop_sha256": read_after_stop,
            "after_repair_sha256": digest2,
            "victim_transfer_port": 19000 + victim,
            "death_detection_ms": detected_ms,
            "repair_observed_ms": repaired_ms,
            "before_state": before_state,
            "death_observed_state": detected,
            "after_state": after_state,
            "before": before,
            "after": after,
            "method": "SIGTERM one owned DataNode process. Four independent data directories, RF=3. Three surviving nodes allow lost replicas to be placed on the surviving node that lacked each block. Polling may miss the brief under-replicated state. Detection time includes the post-stop read and polling; repair time is an observation bound, not exact scheduler latency. Heartbeats=1s, recheck=1000ms, replication check=1s for this lab only. No NameNode HA, racks, host-failure or production throughput test.",
        }
        Path(out or ROOT / "results/hdfs.json").write_text(json.dumps(result, indent=2))
        print(
            "HDFS: 13 blocks, RF=3, stopped DN",
            victim,
            "read equality and replica restoration verified",
            flush=True,
        )
    finally:
        for p in reversed(procs):
            if p.poll() is None:
                p.terminate()
        for p in reversed(procs):
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        for h in handles:
            h.close()


if __name__ == "__main__":
    run()
