#!/usr/bin/env python3
"""Download upstream runtimes into ignored build/vendor; never run an install script."""
import argparse, hashlib, json, platform, tarfile, urllib.request, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "build/vendor"
V.mkdir(parents=True, exist_ok=True)
LOCK = json.loads((ROOT / "runtime-lock.json").read_text())
p = argparse.ArgumentParser()
p.add_argument("profile", choices=["hdfs", "database"])
a = p.parse_args()


def get(url, path):
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".part")
        print("Downloading", url, flush=True)
        offset = tmp.stat().st_size if tmp.exists() else 0
        req = urllib.request.Request(
            url, headers={"Range": f"bytes={offset}-"} if offset else {}
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            mode = "ab" if offset and response.status == 206 else "wb"
            with open(tmp, mode) as f:
                shutil.copyfileobj(response, f, length=1024 * 1024)
        tmp.rename(path)


def extract(tar, keep):
    with tarfile.open(tar) as t:
        for m in t.getmembers():
            parts = Path(m.name).parts
            if m.name.startswith("/") or ".." in parts or m.issym() or m.islnk():
                continue
            if keep(m.name):
                t.extract(m, V)


if a.profile == "hdfs":
    ver = "3.4.2"
    name = f"hadoop-{ver}"
    url = f"https://archive.apache.org/dist/hadoop/common/{name}/{name}.tar.gz"
    archive = V / (name + ".tar.gz")
    get(url, archive)
    get(url + ".sha512", V / (name + ".sha512"))
    digest = hashlib.file_digest(open(archive, "rb"), "sha512").hexdigest()
    text = (V / (name + ".sha512")).read_text()
    assert digest.lower() in text.lower(), "Upstream SHA512 mismatch"
    assert digest == LOCK["hdfs"]["sha512"], "Pinned SHA512 mismatch"
    if not (V / name / "bin/hdfs").exists():
        extract(
            archive,
            lambda n: any(
                n.startswith(f"{name}/{x}")
                for x in [
                    "bin/",
                    "libexec/",
                    "etc/hadoop/",
                    "share/hadoop/common/",
                    "share/hadoop/hdfs/",
                    "LICENSE",
                    "NOTICE",
                ]
            ),
        )
else:
    ver = "24.1.24"
    system = platform.system()
    arch = platform.machine()
    if system not in ("Darwin", "Linux") or (system == "Darwin" and arch != "arm64"):
        raise SystemExit("Supported: macOS arm64; Linux arm64/x86_64")
    tag = (
        "darwin-11.0-arm64"
        if system == "Darwin" and arch == "arm64"
        else "linux-arm64" if arch in ("aarch64", "arm64") else "linux-amd64"
    )
    name = f"cockroach-v{ver}.{tag}"
    url = f"https://binaries.cockroachdb.com/{name}.tgz"
    archive = V / (name + ".tgz")
    get(url, archive)
    if not (V / name / "cockroach").exists():
        extract(archive, lambda n: True)
    digest = hashlib.file_digest(open(archive, "rb"), "sha256").hexdigest()
    get(url + ".sha256sum", V / (name + ".sha256sum"))
    assert digest in (V / (name + ".sha256sum")).read_text(), "Upstream SHA256 mismatch"
    if tag in LOCK["database"]["sha256"]:
        assert digest == LOCK["database"]["sha256"][tag], "Pinned SHA256 mismatch"
record = {
    "profile": a.profile,
    "version": ver,
    "url": url,
    "archive_digest": digest,
    "digest_algorithm": "sha512" if a.profile == "hdfs" else "sha256",
}
(V / (a.profile + "-download.json")).write_text(json.dumps(record, indent=2))
print(json.dumps(record), flush=True)
