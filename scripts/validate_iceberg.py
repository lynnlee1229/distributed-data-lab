#!/usr/bin/env python3
"""Independently validate the explicit learning contract in an Iceberg report."""
import argparse, hashlib, json
from pathlib import Path


def validate(report):
    def require(test, message):
        if not test:
            raise ValueError(message)

    require(report["experiment"] == "iceberg", "Not an Iceberg report")
    snapshots = report["snapshots"]
    require(
        [x["rows"] for x in snapshots] == [3, 5, 6],
        "Snapshot cardinality oracle failed",
    )
    ids = [x["snapshot_id"] for x in snapshots]
    require(len(set(ids)) == 3, "Snapshots must be distinct")
    require(
        snapshots[0]["parent_snapshot_id"] is None, "First snapshot must have no parent"
    )
    require(
        [x["parent_snapshot_id"] for x in snapshots[1:]] == ids[:2],
        "Snapshot lineage is not a chain",
    )
    for s in snapshots:
        require(
            sum(x["record_count"] for x in s["files"]) == s["rows"],
            "Manifest file count disagrees with row count",
        )
    schema = report["schema_evolution"]
    require(
        schema["data_snapshot_id_before"] == schema["data_snapshot_id_after"] == ids[1],
        "Schema-only commit changed the data snapshot",
    )
    before = {x["name"]: x for x in schema["before_fields"]}
    after = {x["name"]: x for x in schema["after_fields"]}
    require(
        before["category"]["id"] == after["topic"]["id"] == 2,
        "Rename lost stable field identity",
    )
    require(
        "category" not in after and after["quality"]["required"] is False,
        "Evolved schema contract failed",
    )
    require(
        schema["before_schema_id"] != schema["after_schema_id"],
        "Schema ID did not change",
    )
    require(
        report["partition_evolution"]["current_file_spec_ids"] == [0, 1],
        "Mixed partition specs missing",
    )
    travel = report["time_travel"]
    require(
        [r["id"] for r in travel["base_rows_after_later_commits"]] == [1, 2, 3],
        "Old snapshot row oracle failed",
    )
    require(
        [r["id"] for r in travel["second_rows_after_later_commits"]] == [1, 2, 3, 4, 5],
        "Second snapshot row oracle failed",
    )
    expected = [
        (1, "storage", "column chunk", None),
        (2, "database", "serializable", None),
        (3, "storage", "replica block", None),
        (4, "database", "index range", None),
        (5, "lakehouse", "snapshot manifest", None),
        (6, "storage", "immutable files", 9),
    ]
    actual = [
        (r["id"], r["topic"], r["text"], r["quality"]) for r in travel["current_rows"]
    ]
    require(actual == expected, "Independent current-row oracle failed")

    def fingerprint(rows):
        return hashlib.sha256(
            json.dumps(
                sorted(rows, key=lambda r: r["id"]),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()

    require(
        fingerprint(travel["base_rows_after_later_commits"])
        == travel["base_logical_sha256_before"]
        == travel["base_logical_sha256_after"],
        "Pinned snapshot changed",
    )
    require(
        fingerprint(travel["current_rows"])
        == travel["current_logical_sha256"]
        != travel["base_logical_sha256_before"],
        "Latest and pinned fingerprints must differ",
    )
    counter = report["counterexample"]
    require(
        counter["committed_ids"] == [1, 2, 3, 4, 5, 6]
        and counter["naive_directory_ids"] == [1, 2, 3, 4, 5, 6, 999],
        "Directory-listing counterexample missing",
    )
    require(
        counter["valid_uncommitted_file"]
        not in {f["path"] for s in snapshots for f in s["files"]},
        "Uncommitted file became table membership",
    )
    metadata = report["metadata_validation"]
    require(
        metadata["current_snapshot_id"] == ids[-1] and metadata["catalog_reopened"],
        "Persisted catalog pointer not checked",
    )
    require(
        metadata["schema_count"] == 2 and metadata["partition_spec_count"] == 2,
        "Metadata evolution counts differ",
    )
    require(
        metadata["original_data_file_hashes_before"]
        == metadata["original_data_file_hashes_after"],
        "A metadata-only change rewrote old file bytes",
    )
    old = [
        x
        for x in metadata["physical_file_schemas"]
        if any(f["name"] == "category" for f in x["fields"])
    ]
    new = [
        x
        for x in metadata["physical_file_schemas"]
        if any(f["name"] == "topic" for f in x["fields"])
    ]
    require(
        len(old) == 2 and len(new) == 1,
        "Expected two old-schema files and one evolved file",
    )
    require(
        all(
            next(
                f["field_id"] for f in x["fields"] if f["name"] in ("category", "topic")
            )
            == "2"
            for x in old + new
        ),
        "Physical Parquet field IDs disagree",
    )
    return {
        "valid": True,
        "properties": [
            "retained snapshot rowsets",
            "schema-only metadata commit",
            "field identity across rename",
            "mixed partition specifications",
            "immutable old file bytes",
            "persisted catalog pointer",
            "uncommitted valid file excluded",
        ],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "report",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "results/iceberg.json",
    )
    a = p.parse_args()
    print(json.dumps(validate(json.loads(a.report.read_text())), indent=2))
