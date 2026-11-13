"""Three actual CockroachDB nodes: cross-range transfer and write-skew conflict."""

import concurrent.futures, datetime, json, os, platform, re, shutil, socket, subprocess, time, urllib.request
from pathlib import Path
import psycopg2, psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
SQL = [19300, 19301, 19302]
HTTP = [19400, 19401, 19402]


def run(out=None):
    candidates = list((ROOT / "build/vendor").glob("cockroach-v24.1.24.*/cockroach"))
    assert candidates, "Run bootstrap.py database first"
    binary = candidates[0]
    work = ROOT / "build/database"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    procs = []
    handles = []
    for port in SQL + HTTP:
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))

    def connect(i=0):
        c = psycopg2.connect(
            host="127.0.0.1",
            port=SQL[i],
            user="root",
            dbname="defaultdb",
            sslmode="disable",
            connect_timeout=3,
            application_name="distributed-data-lab",
        )
        c.autocommit = True
        return c

    def query(c, sql, args=None):
        with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, args)
            return [dict(x) for x in cur.fetchall()] if cur.description else []

    def wait(fn, seconds=90):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                val = fn()
                if val:
                    return val
            except (OSError, psycopg2.Error):
                pass
            time.sleep(1)
        raise RuntimeError("Database readiness timeout")

    env = {
        **os.environ,
        "COCKROACH_SKIP_ENABLING_DIAGNOSTIC_REPORTING": "true",
        "COCKROACH_CRASH_REPORTS": "",
        "COCKROACH_AUTO_BALLAST": "false",
    }
    try:
        for i in range(3):
            h = open(work / f"node{i}.log", "wb")
            handles.append(h)
            args = [
                str(binary),
                "start",
                "--insecure",
                f"--listen-addr=127.0.0.1:{SQL[i]}",
                f"--http-addr=127.0.0.1:{HTTP[i]}",
                f'--store={work/f"node{i}"},ballast-size=0',
                "--join=" + ",".join(f"127.0.0.1:{p}" for p in SQL),
                "--cache=64MiB",
                "--max-sql-memory=64MiB",
                "--locality=labnode=" + str(i + 1),
            ]
            procs.append(subprocess.Popen(args, env=env, stdout=h, stderr=h))
        time.sleep(3)
        subprocess.run(
            [str(binary), "init", "--insecure", "--host=127.0.0.1:19300"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=60,
        )
        c = wait(lambda: connect())
        query(c, "SET CLUSTER SETTING diagnostics.reporting.enabled = false")
        query(c, "SET CLUSTER SETTING diagnostics.reporting.send_crash_reports = false")
        version = query(c, "SELECT version() AS version")[0]["version"]
        query(
            c,
            "CREATE TABLE accounts (id INT PRIMARY KEY, balance INT NOT NULL CHECK(balance>=0))",
        )
        query(c, "INSERT INTO accounts VALUES (1,100),(1001,100),(2001,100)")
        query(c, "ALTER TABLE accounts SPLIT AT VALUES (1000),(2000)")
        ranges = wait(
            lambda: (
                r
                if len(r := query(c, "SHOW RANGES FROM TABLE accounts WITH DETAILS"))
                >= 3
                and all(len(x["replicas"]) == 3 for x in r)
                else False
            ),
            120,
        )
        # Explicitly move leases, then verify instead of inferring placement from process count.
        for i, r in enumerate(sorted(ranges, key=lambda x: x["range_id"])):
            query(c, f"ALTER RANGE {r['range_id']} RELOCATE LEASE TO {i%3+1}")
        ranges = query(c, "SHOW RANGES FROM TABLE accounts WITH DETAILS")
        assert len(set(r["lease_holder"] for r in ranges)) >= 2
        nodes = query(
            c,
            "SELECT node_id, address FROM crdb_internal.gossip_nodes ORDER BY node_id",
        )
        assert len(nodes) == 3

        def metrics():
            out = []
            for i, port in enumerate(HTTP):
                text = (
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/_status/vars", timeout=5
                    )
                    .read()
                    .decode()
                )
                vals = {}
                for line in text.splitlines():
                    if line.startswith("#"):
                        continue
                    name = line.split(" ")[0].split("{")[0]
                    if re.fullmatch(
                        r"(sql_txn_(commit|abort|begin)_count|txn_restarts_serializable|txn_restarts_writetooold|txn_commits|txn_aborts)",
                        name,
                    ):
                        try:
                            vals[name] = float(line.split()[-1])
                        except ValueError:
                            pass
                out.append({"http_port": port, "counters": vals})
            return out

        before_metrics = metrics()
        query(c, "SET tracing=on,kv")
        query(c, "BEGIN")
        query(c, "UPDATE accounts SET balance=balance-7 WHERE id=1")
        query(c, "UPDATE accounts SET balance=balance+7 WHERE id=1001")
        query(c, "COMMIT")
        query(c, "SET tracing=off")
        trace = query(c, "SHOW KV TRACE FOR SESSION")
        events = []
        for row in trace:
            message = str(row.get("message", ""))
            if any(
                s in message
                for s in ["Put ", "CPut ", "Get ", "EndTxn", "r", "sending batch"]
            ):
                events.append(
                    {
                        k: str(v)
                        for k, v in row.items()
                        if k in ["message", "operation", "age", "location"]
                    }
                )
        transferred = query(c, "SELECT * FROM accounts ORDER BY id")
        assert [r["balance"] for r in transferred] == [93, 107, 100]
        # A classic write-skew schedule: both read the same total, then write disjoint keys.
        # A result delivered to each client prevents silent replay across its earlier read.
        a, b = connect(0), connect(1)
        query(a, "BEGIN ISOLATION LEVEL SERIALIZABLE")
        query(b, "BEGIN ISOLATION LEVEL SERIALIZABLE")
        reads = [
            query(x, "SELECT SUM(balance)::INT AS total FROM accounts")[0]["total"]
            for x in (a, b)
        ]
        assert reads == [300, 300]
        query(a, "UPDATE accounts SET balance=balance-80 WHERE id=1")
        query(b, "UPDATE accounts SET balance=balance-80 WHERE id=1001")

        def commit(label, conn):
            start = time.perf_counter()
            try:
                query(conn, "COMMIT")
                return {
                    "client": label,
                    "status": "committed",
                    "sqlstate": "00000",
                    "elapsed_ms": (time.perf_counter() - start) * 1000,
                }
            except psycopg2.Error as e:

                try:
                    query(conn, "ROLLBACK")
                except psycopg2.Error as rollback_error:
                    if rollback_error.pgcode != "25P01":
                        raise
                return {
                    "client": label,
                    "status": "retry_required",
                    "sqlstate": e.pgcode,
                    "message": e.diag.message_primary,
                    "elapsed_ms": (time.perf_counter() - start) * 1000,
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda pair: commit(*pair), [("A", a), ("B", b)]))
        a.close()
        b.close()
        assert sum(x["status"] == "committed" for x in outcomes) == 1 and any(
            x["sqlstate"] == "40001" for x in outcomes
        ), outcomes
        after_conflict = query(c, "SELECT * FROM accounts ORDER BY id")
        assert sum(x["balance"] for x in after_conflict) == 220
        # Retry the entire failed business transaction against fresh state: total-80<220, so decline.
        retry_read = query(c, "SELECT SUM(balance)::INT AS total FROM accounts")[0][
            "total"
        ]
        retry = {
            "fresh_total": retry_read,
            "minimum_total": 220,
            "withdrawal": 80,
            "decision": "declined" if retry_read - 80 < 220 else "allowed",
        }
        assert retry["decision"] == "declined"
        plan = query(c, "EXPLAIN ANALYZE SELECT SUM(balance) FROM accounts")
        plan_lines = [str(next(iter(x.values()))) for x in plan]
        plan_lines = [s for s in plan_lines if "http" not in s]
        after_metrics = metrics()
        final = query(c, "SELECT * FROM accounts ORDER BY id")
        c.close()
        result = {
            "experiment": "database",
            "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "version": version,
            "topology": {
                "nodes": nodes,
                "replicas_per_range": 3,
                "single_host": True,
                "bind": "127.0.0.1",
                "each_node_cache_mib": 64,
                "each_node_sql_mib": 64,
            },
            "ranges": ranges,
            "transfer": {
                "before": [100, 100, 100],
                "after": transferred,
                "amount": 7,
                "sum": 300,
                "kv_trace": events,
            },
            "conflict": {
                "schedule": "Both SERIALIZABLE transactions read total=300; A subtracts 80 at id=1, B at id=1001; commits concurrently. Business rule: remaining total >=220.",
                "read_totals": reads,
                "outcomes": outcomes,
                "after": after_conflict,
                "retry": retry,
                "final": final,
            },
            "plan": plan_lines,
            "metrics_before": before_metrics,
            "metrics_after": after_metrics,
            "method": "Real three-process cluster, replicated ranges and verified distinct leaseholders. A cross-range transfer commits two updates atomically; a separate write-skew schedule on distinct keys produces a real 40001 error without fault injection. Timing is diagnostic only. No network partition, node-failure, multi-host scaling, production capacity or disk durability validation. Binary is a pinned non-production teaching baseline; no paid feature or cloud account used.",
        }
        Path(out or ROOT / "results/database.json").write_text(
            json.dumps(result, indent=2, default=str)
        )
        print(
            "Database: 3 nodes, leases on",
            sorted(set(r["lease_holder"] for r in ranges)),
            "cross-range transfer and 40001 verified",
            flush=True,
        )
    finally:
        for p in reversed(procs):
            if p.poll() is None:
                p.terminate()
        for p in reversed(procs):
            try:
                p.wait(timeout=25)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        for h in handles:
            h.close()


if __name__ == "__main__":
    run()
