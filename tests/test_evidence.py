"""Check scientific invariants in real exported evidence, not timing thresholds."""

import hashlib, json, re, unittest
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"


class Evidence(unittest.TestCase):
    def load(self, n):
        return json.loads((R / (n + ".json")).read_text())

    def test_parquet(self):
        d = self.load("parquet")
        self.assertEqual(len(d["variants"]), 5)
        for v in d["variants"]:
            self.assertTrue(v["logical_equal"])
            self.assertEqual(len(v["runs"]), 9)
            for r in v["runs"]:
                self.assertTrue(r["equal"])
                self.assertEqual(
                    {k: r[k] for k in ["rows", "id_sum", "value_sum"]}, d["expected"]
                )
                self.assertEqual(
                    r["engine_requested_bytes"],
                    sum(x["bytes"] for x in r["read_calls"]),
                )
                for span in r["read_calls"]:
                    self.assertGreaterEqual(span["offset"], 0)
                    self.assertLessEqual(
                        span["offset"] + span["bytes"], v["metadata"]["file_bytes"]
                    )
        variants = {v["name"]: v for v in d["variants"]}
        self.assertEqual(
            variants["sorted-4096-zstd"]["metadata"]["candidate_groups"], 2
        )
        self.assertEqual(
            variants["shuffled-4096-zstd"]["metadata"]["candidate_groups"], 32
        )
        self.assertLess(
            variants["sorted-4096-zstd"]["runs"][1]["engine_requested_bytes"],
            variants["shuffled-4096-zstd"]["runs"][1]["engine_requested_bytes"],
        )

    def test_hdfs_repair(self):
        d = self.load("hdfs")
        self.assertEqual(d["topology"]["replication_factor"], 3)
        self.assertEqual(d["before_state"]["NumLiveDataNodes"], 4)
        self.assertEqual(d["after_state"]["NumLiveDataNodes"], 3)
        self.assertEqual(d["after_state"]["NumDeadDataNodes"], 1)
        self.assertEqual(d["after_state"]["UnderReplicatedBlocks"], 0)
        self.assertEqual(d["after_state"]["PendingReplicationBlocks"], 0)
        self.assertEqual(d["sha256"], d["after_stop_sha256"])
        self.assertEqual(d["sha256"], d["after_repair_sha256"])
        before = {b["block"]: b for b in d["before"]["blocks"]}
        after = {b["block"]: b for b in d["after"]["blocks"]}
        self.assertEqual(set(before), set(after))
        self.assertEqual(len(after), 13)
        changed = False
        for key, b in after.items():
            self.assertEqual(b["live_replicas"], 3)
            self.assertEqual(len(set(b["locations"])), 3)
            self.assertNotIn(str(d["victim_transfer_port"]), b["locations"])
            changed |= set(b["locations"]) != set(before[key]["locations"])
        self.assertTrue(
            changed, "Need actual replacement placements, not just a successful read"
        )

    def test_distributed_transaction(self):
        d = self.load("database")
        self.assertEqual(len(d["topology"]["nodes"]), 3)
        self.assertGreaterEqual(len(set(r["lease_holder"] for r in d["ranges"])), 2)
        for r in d["ranges"]:
            self.assertEqual(len(set(r["replicas"])), 3)
        self.assertEqual([r["balance"] for r in d["transfer"]["after"]], [93, 107, 100])
        self.assertEqual(d["conflict"]["read_totals"], [300, 300])
        self.assertEqual(
            sorted(x["sqlstate"] for x in d["conflict"]["outcomes"]), ["00000", "40001"]
        )
        self.assertEqual(sum(x["balance"] for x in d["conflict"]["final"]), 220)
        self.assertEqual(d["conflict"]["retry"]["decision"], "declined")
        targets = set()
        for event in d["transfer"]["kv_trace"]:
            m = re.search(r"sending batch .* Put to \(n(\d+),", event["message"])
            if m:
                targets.add(m[1])
        self.assertGreaterEqual(
            len(targets), 2, "Need actual writes to distinct serving nodes"
        )
        self.assertTrue(any("n1, n2, n3" in line for line in d["plan"]))

    def test_result_manifest(self):
        p = R / "index.json"
        if not p.exists():
            self.skipTest("Manifest generated after integration profiles")
        for name, record in json.loads(p.read_text())["files"].items():
            self.assertEqual(
                hashlib.sha256((R / name).read_bytes()).hexdigest(), record["sha256"]
            )


if __name__ == "__main__":
    unittest.main()
