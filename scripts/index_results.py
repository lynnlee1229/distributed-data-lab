#!/usr/bin/env python3
import hashlib, json
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
files = {
    p.name: {
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "bytes": p.stat().st_size,
    }
    for p in (R / (n + ".json") for n in ["parquet", "hdfs", "database"])
}
(R / "index.json").write_text(
    json.dumps(
        {
            "scope": "actual synthetic local measurements; sanitized fields only; single host",
            "files": files,
        },
        indent=2,
    )
)
