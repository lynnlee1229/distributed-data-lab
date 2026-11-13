#!/usr/bin/env python3
"""Sequential, bounded profiles. Shared machines may set DDS_RESOURCE_LOCK."""
import argparse, datetime, json, os, subprocess, sys, uuid, signal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument("profile", choices=["parquet", "hdfs", "database", "iceberg", "all"])
p.add_argument("--smoke", action="store_true")
a = p.parse_args()
lock = Path(os.environ.get("DDS_RESOURCE_LOCK", ROOT / "build/runtime.lock"))
lock.parent.mkdir(parents=True, exist_ok=True)
nonce = uuid.uuid4().hex
try:
    lock.mkdir()
except FileExistsError:
    raise SystemExit(
        "Runtime lock occupied: "
        + str(lock)
        + "; inspect its owner, never delete another run’s lock."
    )
(lock / "owner.json").write_text(
    json.dumps(
        {
            "lab": "distributed-data-lab",
            "nonce": nonce,
            "acquired_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )
)
try:
    for profile in (
        ["parquet", "hdfs", "database"] if a.profile == "all" else [a.profile]
    ):
        script = {
            "parquet": "parquet_layout.py",
            "hdfs": "hdfs_recovery.py",
            "database": "distributed_transactions.py",
            "iceberg": "iceberg_snapshots.py",
        }[profile]
        args = [sys.executable, str(ROOT / "experiments" / script)]
        if a.smoke and profile == "parquet":
            args += ["--smoke", "--out", str(ROOT / "build/smoke-parquet.json")]
        proc = subprocess.Popen(args, cwd=ROOT, start_new_session=True)
        try:
            code = proc.wait(timeout=600)
            if code:
                raise subprocess.CalledProcessError(code, args)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
finally:
    if (lock / "owner.json").exists() and json.loads(
        (lock / "owner.json").read_text()
    ).get("nonce") == nonce:
        (lock / "owner.json").unlink()
        lock.rmdir()
