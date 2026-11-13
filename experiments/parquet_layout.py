"""Seeded, equal-result Parquet layout experiments; counted engine read requests."""

import gc, hashlib, io, json, random, time
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc

ROOT = Path(__file__).resolve().parents[1]


class CountedFile(io.RawIOBase):
    def __init__(self, path):
        self.f = open(path, "rb")
        self.reads = []

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.f.tell()

    def seek(self, *a):
        return self.f.seek(*a)

    def read(self, n=-1):
        offset = self.f.tell()
        data = self.f.read(n)
        self.reads.append({"offset": offset, "bytes": len(data)})
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)

    def close(self):
        if not self.closed:
            self.f.close()
        super().close()


def metadata(path, lo=32000, hi=33023):
    f = pq.ParquetFile(path)
    groups = []
    for i in range(f.num_row_groups):
        r = f.metadata.row_group(i)
        cols = []
        for j in range(r.num_columns):
            c = r.column(j)
            s = c.statistics
            cols.append(
                {
                    "path": c.path_in_schema,
                    "physical_type": c.physical_type,
                    "codec": c.compression,
                    "encodings": list(c.encodings),
                    "compressed_bytes": c.total_compressed_size,
                    "uncompressed_bytes": c.total_uncompressed_size,
                    "min": s.min if s and s.has_min_max else None,
                    "max": s.max if s and s.has_min_max else None,
                    "null_count": s.null_count if s else None,
                }
            )
        key = cols[0]
        candidate = key["min"] is None or not (key["max"] < lo or key["min"] > hi)
        groups.append(
            {"index": i, "rows": r.num_rows, "candidate": candidate, "columns": cols}
        )
    return {
        "rows": f.metadata.num_rows,
        "file_bytes": path.stat().st_size,
        "row_groups": groups,
        "candidate_groups": sum(g["candidate"] for g in groups),
        "candidate_projected_chunk_bytes": sum(
            c["compressed_bytes"]
            for g in groups
            if g["candidate"]
            for c in g["columns"]
            if c["path"] in ["id", "value"]
        ),
    }


def run(smoke=False, out=None):
    n = 65536 if smoke else 131072
    seed = 9162026
    work = ROOT / "build/parquet"
    work.mkdir(parents=True, exist_ok=True)
    base = pa.table(
        {
            "id": pa.array(range(n), type=pa.int64()),
            "value": pa.array([(i * 7) % 1009 for i in range(n)], type=pa.int64()),
            "bucket": [f"b{i%32:02}" for i in range(n)],
            "payload": [
                hashlib.sha256(f"{seed}:{i}".encode()).hexdigest() for i in range(n)
            ],
        }
    )
    ids = list(range(n))
    random.Random(seed).shuffle(ids)
    shuffled = base.take(pa.array(ids))
    lo, hi = 32000, 33023
    expected = base.filter(
        pc.and_(pc.greater_equal(base["id"], lo), pc.less_equal(base["id"], hi))
    ).select(["id", "value"])
    reports = []
    variants = [
        ("shuffled", 4096, "zstd"),
        ("sorted", 4096, "zstd"),
        ("shuffled", 32768, "zstd"),
        ("sorted", 32768, "zstd"),
        ("sorted", 4096, "snappy"),
    ]
    for order, rg, codec in variants:
        path = work / f"{order}-{rg}-{codec}.parquet"
        pq.write_table(
            base if order == "sorted" else shuffled,
            path,
            row_group_size=rg,
            compression=codec,
            use_dictionary=["bucket"],
            write_statistics=True,
        )
        all_rows = pq.read_table(path).sort_by("id")
        assert all_rows.equals(base), "Logical dataset differs"
        report = {
            "name": path.stem,
            "row_group_target": rg,
            "order": order,
            "codec": codec,
            "logical_equal": True,
            "metadata": metadata(path),
            "runs": [],
        }

        def query(mode):
            source = CountedFile(path)
            with pa.PythonFile(source, mode="r") as stream:
                start = time.perf_counter()
                table = pq.read_table(
                    stream,
                    columns=None if mode == "wide_filter" else ["id", "value"],
                    filters=(
                        None
                        if mode == "projected_no_pushdown"
                        else [("id", ">=", lo), ("id", "<=", hi)]
                    ),
                    use_threads=False,
                    pre_buffer=False,
                )
                if mode == "projected_no_pushdown":
                    table = table.filter(
                        pc.and_(
                            pc.greater_equal(table["id"], lo),
                            pc.less_equal(table["id"], hi),
                        )
                    )
                result = table.select(["id", "value"]).sort_by("id")
                elapsed = (time.perf_counter() - start) * 1000
                assert result.equals(expected), "Query result differs"
                reads = list(source.reads)
            return {
                "mode": mode,
                "elapsed_ms": elapsed,
                "engine_requested_bytes": sum(x["bytes"] for x in reads),
                "read_calls": reads,
                "rows": result.num_rows,
                "id_sum": sum(result["id"].to_pylist()),
                "value_sum": sum(result["value"].to_pylist()),
                "equal": True,
            }

        modes = ["wide_filter", "projected_filter", "projected_no_pushdown"]
        for mode in modes:
            query(mode)  # warm-up
        for rep in range(3):
            for mode in modes if rep % 2 == 0 else list(reversed(modes)):
                report["runs"].append({"repeat": rep + 1, **query(mode)})
        reports.append(report)
    result = {
        "experiment": "parquet",
        "executed_at": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
        "versions": {"pyarrow": pa.__version__},
        "seed": seed,
        "rows": n,
        "predicate": {"column": "id", "lower_inclusive": lo, "upper_inclusive": hi},
        "expected": {
            "rows": expected.num_rows,
            "id_sum": sum(expected["id"].to_pylist()),
            "value_sum": sum(expected["value"].to_pylist()),
        },
        "method": "One warm-up per mode, three measured alternating-order repetitions. Engine-requested read bytes are counted at Python file read(), may include overlapping metadata reads and cache hits; not physical disk or network bytes. Candidate chunk bytes are only a footer-based estimate, excluding metadata, page indexes and read coalescing. Timings include read/filter/sort but exclude validation, file generation and process startup. OS cache is not flushed.",
        "variants": reports,
    }
    target = Path(out or ROOT / "results/parquet.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print(
        "Parquet:",
        n,
        "rows;",
        len(reports) * 9,
        "equal-result measured runs",
        flush=True,
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--out")
    a = p.parse_args()
    run(a.smoke, a.out)
