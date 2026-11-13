"""Real local Iceberg commits, schema/partition evolution, and a membership counterexample.

No cloud, API key, deletes, snapshot expiration, or destructive maintenance. Every
run creates an exclusive directory. All expected rowsets are literal independent
oracles; snapshot IDs and file names are genuine runtime-generated values.
"""

from __future__ import annotations
import argparse, datetime, hashlib, json, sqlite3, uuid
from pathlib import Path
from urllib.parse import unquote, urlsplit
import pyarrow as pa
import pyarrow.parquet as pq
import pyiceberg
import sqlalchemy
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.expressions import EqualTo
from pyiceberg.types import IntegerType

ROOT = Path(__file__).resolve().parents[1]
# Explicit expected rowsets, separate from the writer batches and reader logic.
EXPECTED_BASE = [
    {"id": 1, "category": "storage", "text": "column chunk"},
    {"id": 2, "category": "database", "text": "serializable"},
    {"id": 3, "category": "storage", "text": "replica block"},
]
EXPECTED_SECOND = EXPECTED_BASE + [
    {"id": 4, "category": "database", "text": "index range"},
    {"id": 5, "category": "lakehouse", "text": "snapshot manifest"},
]
EXPECTED_CURRENT = [
    {"id": 1, "topic": "storage", "text": "column chunk", "quality": None},
    {"id": 2, "topic": "database", "text": "serializable", "quality": None},
    {"id": 3, "topic": "storage", "text": "replica block", "quality": None},
    {"id": 4, "topic": "database", "text": "index range", "quality": None},
    {"id": 5, "topic": "lakehouse", "text": "snapshot manifest", "quality": None},
    {"id": 6, "topic": "storage", "text": "immutable files", "quality": 9},
]


def canonical(rows):
    return sorted(rows, key=lambda r: r["id"])


def digest_rows(rows):
    return hashlib.sha256(
        json.dumps(
            canonical(rows), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def run(out=None):
    run_id = (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:10]
    )
    work = ROOT / "build/iceberg" / run_id
    work.mkdir(parents=True, exist_ok=False)
    warehouse = work / "warehouse"

    # A raw Unicode path avoids percent-escaped file:// paths being treated as
    # literal filesystem names by this pinned PyIceberg/Arrow combination.
    def catalog():
        return SqlCatalog(
            "distributed_data_lab_local",
            uri="sqlite:///" + str(work / "catalog.db"),
            warehouse=str(warehouse),
            **{"py-io-impl": "pyiceberg.io.pyarrow.PyArrowFileIO"},
        )

    c = catalog()
    c.create_namespace("lab")
    schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("category", pa.string()),
            pa.field("text", pa.string()),
        ]
    )
    t = c.create_table("lab.corpus", schema=schema, properties={"format-version": "2"})

    def path(uri):
        parsed = urlsplit(uri)
        p = Path(unquote(parsed.path) if parsed.scheme == "file" else uri).resolve()
        assert p.is_relative_to(work.resolve()), "Unexpected non-local data reference"
        return p

    def relative(uri):
        return str(path(uri).relative_to(work.resolve()))

    def rows(scan):
        return canonical(scan.to_arrow().to_pylist())

    def file_records(scan):
        return sorted(
            [
                {
                    "path": relative(x.file.file_path),
                    "spec_id": x.file.spec_id,
                    "record_count": x.file.record_count,
                    "file_bytes": x.file.file_size_in_bytes,
                }
                for x in scan.plan_files()
            ],
            key=lambda x: x["path"],
        )

    def fields():
        return [
            {
                "id": f.field_id,
                "name": f.name,
                "type": str(f.field_type),
                "required": f.required,
            }
            for f in t.schema().fields
        ]

    # Batches are explicit writer inputs; expected results above are a separate contract.
    t.append(
        pa.Table.from_pylist(
            [
                {"id": 1, "category": "storage", "text": "column chunk"},
                {"id": 2, "category": "database", "text": "serializable"},
                {"id": 3, "category": "storage", "text": "replica block"},
            ],
            schema=schema,
        )
    )
    s1 = t.current_snapshot().snapshot_id
    base_rows = rows(t.scan())
    assert base_rows == EXPECTED_BASE
    metadata_s1 = t.metadata_location
    files_s1 = file_records(t.scan())
    base_hash = digest_rows(base_rows)
    t.append(
        pa.Table.from_pylist(
            [
                {"id": 4, "category": "database", "text": "index range"},
                {"id": 5, "category": "lakehouse", "text": "snapshot manifest"},
            ],
            schema=schema,
        )
    )
    s2 = t.current_snapshot().snapshot_id
    second_rows = rows(t.scan())
    assert second_rows == EXPECTED_SECOND
    original_files = {
        x["path"]: hashlib.sha256((work / x["path"]).read_bytes()).hexdigest()
        for x in file_records(t.scan())
    }
    before_fields = fields()
    before_schema_id = t.schema().schema_id
    with t.update_schema() as update:
        update.rename_column("category", "topic").add_column("quality", IntegerType())
    after_fields = fields()
    schema_snapshot_after = t.current_snapshot().snapshot_id
    assert (
        t.current_snapshot().snapshot_id == s2
    ), "Schema metadata update unexpectedly created a data snapshot"
    assert (
        next(f["id"] for f in before_fields if f["name"] == "category")
        == next(f["id"] for f in after_fields if f["name"] == "topic")
        == 2
    )
    assert t.schema().schema_id != before_schema_id
    current_after_schema = rows(t.scan())
    assert current_after_schema == EXPECTED_CURRENT[:5]
    pinned_after_schema = rows(t.scan(snapshot_id=s2))
    assert pinned_after_schema == EXPECTED_SECOND
    # A metadata-only partition change; existing data files keep spec 0.
    old_spec = t.spec().spec_id
    with t.update_spec() as update:
        update.add_identity("topic")
    new_spec = t.spec().spec_id
    assert old_spec == 0 and new_spec == 1
    assert t.current_snapshot().snapshot_id == s2
    evolved_schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("topic", pa.string()),
            pa.field("text", pa.string()),
            pa.field("quality", pa.int32()),
        ]
    )
    t.append(
        pa.Table.from_pylist(
            [{"id": 6, "topic": "storage", "text": "immutable files", "quality": 9}],
            schema=evolved_schema,
        )
    )
    s3 = t.current_snapshot().snapshot_id
    current_rows = rows(t.scan())
    assert current_rows == EXPECTED_CURRENT
    files_current = file_records(t.scan())
    assert {x["spec_id"] for x in files_current} == {0, 1}
    unchanged = {
        name: hashlib.sha256((work / name).read_bytes()).hexdigest()
        for name in original_files
    }
    assert unchanged == original_files
    # Re-read genuine retained snapshots after all later commits.
    past1 = rows(t.scan(snapshot_id=s1))
    past2 = rows(t.scan(snapshot_id=s2))
    assert past1 == EXPECTED_BASE and past2 == EXPECTED_SECOND
    assert digest_rows(past1) == base_hash and digest_rows(current_rows) != base_hash
    storage_rows = rows(t.scan(row_filter=EqualTo("topic", "storage")))
    assert storage_rows == [EXPECTED_CURRENT[i] for i in [0, 2, 5]]
    # This file is a valid Parquet object but never committed to Iceberg metadata.
    data_dir = path(t.location()) / "data"
    data_dir.mkdir(exist_ok=True)
    orphan = data_dir / "uncommitted-example.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "id": 999,
                    "topic": "storage",
                    "text": "uncommitted poison",
                    "quality": 999,
                }
            ],
            schema=evolved_schema,
        ),
        orphan,
    )
    assert pq.ParquetFile(orphan).metadata.num_rows == 1
    naive = []
    for file in sorted(data_dir.rglob("*.parquet")):
        naive.extend(pq.ParquetFile(file).read(columns=["id"]).column("id").to_pylist())
    committed_ids = [r["id"] for r in rows(t.scan())]
    assert committed_ids == [1, 2, 3, 4, 5, 6]
    assert sorted(naive) == [1, 2, 3, 4, 5, 6, 999]
    assert relative(str(orphan)) not in {f["path"] for f in file_records(t.scan())}
    # Reopen SQLite catalog to check persisted pointer, not just an in-memory Table.
    reloaded = catalog().load_table("lab.corpus")
    assert reloaded.current_snapshot().snapshot_id == s3
    assert rows(reloaded.scan()) == EXPECTED_CURRENT
    metadata_path = path(t.metadata_location)
    raw = json.loads(metadata_path.read_text())
    assert raw["format-version"] == 2 and raw["current-snapshot-id"] == s3
    assert (
        raw["current-schema-id"] == t.schema().schema_id and raw["default-spec-id"] == 1
    )
    snaps = {x["snapshot-id"]: x for x in raw["snapshots"]}
    assert set(snaps) == {s1, s2, s3}
    assert snaps[s1].get("parent-snapshot-id") is None
    assert snaps[s2]["parent-snapshot-id"] == s1
    assert snaps[s3]["parent-snapshot-id"] == s2
    expected_counts = {s1: 3, s2: 5, s3: 6}
    snapshots = []
    for label, sid in [("base", s1), ("second_append", s2), ("evolved_append", s3)]:
        snap = snaps[sid]
        files = file_records(t.scan(snapshot_id=sid))
        assert sum(x["record_count"] for x in files) == expected_counts[sid]
        assert int(snap["summary"]["total-records"]) == expected_counts[sid]
        snapshots.append(
            {
                "label": label,
                "snapshot_id": str(sid),
                "parent_snapshot_id": (
                    str(snap["parent-snapshot-id"])
                    if snap.get("parent-snapshot-id")
                    else None
                ),
                "schema_id": snap["schema-id"],
                "rows": expected_counts[sid],
                "manifest_list": relative(snap["manifest-list"]),
                "files": files,
                "summary": snap["summary"],
            }
        )
    result = {
        "experiment": "iceberg",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "versions": {
            "pyiceberg": pyiceberg.__version__,
            "pyarrow": pa.__version__,
            "sqlalchemy": sqlalchemy.__version__,
            "sqlite": sqlite3.sqlite_version,
        },
        "table_format_version": 2,
        "data_source": "six enumerated synthetic records and one explicitly uncommitted synthetic counterexample; no personal data",
        "scope": "single-process local SQLite catalog and filesystem; not a distributed catalog, cloud, SQL-engine interoperability, concurrency or AI-quality benchmark",
        "snapshots": snapshots,
        "schema_evolution": {
            "before_schema_id": before_schema_id,
            "after_schema_id": t.schema().schema_id,
            "before_fields": before_fields,
            "after_fields": after_fields,
            "data_snapshot_unchanged_during_schema_commit": True,
            "data_snapshot_id_before": str(s2),
            "data_snapshot_id_after": str(schema_snapshot_after),
            "current_projection_after_schema": current_after_schema,
            "explicit_snapshot_projection_after_schema": pinned_after_schema,
            "note": "PyIceberg 0.10.0 scan() uses current table schema; scan(snapshot_id=...) uses the stored snapshot schema. A schema-only metadata commit does not itself create a new data snapshot.",
        },
        "partition_evolution": {
            "old_spec_id": old_spec,
            "new_spec_id": new_spec,
            "current_file_spec_ids": sorted({x["spec_id"] for x in files_current}),
            "files": files_current,
            "filtered_storage_rows": storage_rows,
            "filtered_plan_files": file_records(
                t.scan(row_filter=EqualTo("topic", "storage"))
            ),
            "note": "Old spec-0 files remain candidates where partition metadata cannot reject them; a true row predicate is still applied. File plans are not physical I/O counters.",
        },
        "time_travel": {
            "base_rows_after_later_commits": past1,
            "second_rows_after_later_commits": past2,
            "current_rows": current_rows,
            "base_logical_sha256_before": base_hash,
            "base_logical_sha256_after": digest_rows(past1),
            "current_logical_sha256": digest_rows(current_rows),
            "hash_definition": "SHA256 of JSON rows sorted by id, object keys sorted, compact UTF-8, schema column names retained",
        },
        "counterexample": {
            "valid_uncommitted_file": relative(str(orphan)),
            "uncommitted_row_id": 999,
            "committed_ids": committed_ids,
            "naive_directory_ids": sorted(naive),
            "uncommitted_file_excluded_by_table_scan": True,
            "note": "The extra file is valid Parquet, but no committed Iceberg manifest references it. Directory globbing is not a committed table read. No file or snapshot is removed.",
        },
        "metadata_validation": {
            "current_metadata_file": relative(t.metadata_location),
            "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
            "first_metadata_file": relative(metadata_s1),
            "current_snapshot_id": str(s3),
            "schema_count": len(raw["schemas"]),
            "partition_spec_count": len(raw["partition-specs"]),
            "catalog_reopened": True,
            "schemas": [
                {"schema_id": x["schema-id"], "fields": x["fields"]}
                for x in raw["schemas"]
            ],
            "partition_specs": raw["partition-specs"],
            "original_data_file_hashes_before": original_files,
            "original_data_file_hashes_after": unchanged,
            "old_data_files_unchanged": True,
            "physical_file_schemas": [
                {
                    "path": x["path"],
                    "fields": [
                        {
                            "name": f.name,
                            "field_id": (
                                f.metadata.get(b"PARQUET:field_id", b"").decode()
                                if f.metadata
                                else None
                            ),
                        }
                        for f in pq.ParquetFile(work / x["path"]).schema_arrow
                    ],
                }
                for x in files_current
            ],
        },
        "local_artifact_directory": str(work.relative_to(ROOT)),
        "all_oracles_passed": True,
    }
    target = Path(out or ROOT / "results/iceberg.json")
    target.parent.mkdir(exist_ok=True, parents=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(
        "Iceberg: real snapshots 3/5/6 rows; field ID 2 retained; specs 0+1; old snapshots stable; valid uncommitted id=999 excluded",
        flush=True,
    )
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out")
    a = p.parse_args()
    run(a.out)
