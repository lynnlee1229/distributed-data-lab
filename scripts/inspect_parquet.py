#!/usr/bin/env python3
"""Inspect locally; never upload a file."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.parquet_layout import metadata

p = argparse.ArgumentParser()
p.add_argument("file", type=Path)
p.add_argument("--lower", type=int, default=32000)
p.add_argument("--upper", type=int, default=33023)
a = p.parse_args()
print(json.dumps(metadata(a.file, a.lower, a.upper), indent=2, default=str))
