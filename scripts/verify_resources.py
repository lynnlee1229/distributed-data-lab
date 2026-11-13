#!/usr/bin/env python3
"""Validate the searchable resource inventory; optional bounded live URL checks."""
import argparse, datetime, json, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(data):
    courses = {c["id"]: c for c in data["courses"]}
    resources = {r["id"]: r for r in data["resources"]}
    assert 1 <= len(courses) <= 3 and len(resources) == len(data["resources"])
    for course in courses.values():
        for k in [
            "school",
            "course_number",
            "course_name",
            "term",
            "prerequisites",
            "prerequisite_source",
            "access",
            "solution_policy",
            "verified_on",
        ]:
            assert course.get(k), k
        datetime.date.fromisoformat(course["verified_on"])
    for r in resources.values():
        assert r["status"] == "published" and r["verified_on"] and r["locator"]
        if r["course_id"]:
            assert r["course_id"] in courses
        u = urllib.parse.urlsplit(r["url"])
        assert u.scheme == "https" and u.hostname
        assert u.hostname in {
            "15445.courses.cs.cmu.edu",
            "dsg.csail.mit.edu",
            "hadoop.apache.org",
            "research.google",
            "py.iceberg.apache.org",
            "iceberg.apache.org",
            "parquet.apache.org",
        }
    assert {u["unit"] for u in data["unit_mappings"]} == {
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
    }
    for unit in data["unit_mappings"]:
        assert (
            unit["exercise_commands"]
            and unit["task"]["en"]
            and unit["task"]["zh"]
            and unit["check"]["en"]
            and unit["check"]["zh"]
        )
        assert (
            unit["exercise_origin"]
            == "original companion exercise; not a university assignment solution"
        )
        for id in unit["resources"]:
            assert id in resources
    assert data["ai_extension"]["resource"] in resources
    return {
        "courses": len(courses),
        "resources": len(resources),
        "units": 6,
        "verified_on": data["verified_on"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    a = p.parse_args()
    d = json.loads((ROOT / "data/resources.json").read_text())
    result = validate(d)
    if a.live:
        checks = []
        for r in d["resources"]:
            req = urllib.request.Request(
                urllib.parse.urldefrag(r["url"])[0],
                headers={
                    "Range": "bytes=0-2047",
                    "User-Agent": "Distributed-Data-Lab-resource-verification/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as f:
                prefix = f.read(2048)
                assert f.status in (200, 206)
            if r["url"].endswith(".pdf"):
                assert prefix.startswith(b"%PDF")
            checks.append({"id": r["id"], "url": r["url"], "readable": True})
        result["live_checks"] = checks
    print(json.dumps(result, indent=2))
