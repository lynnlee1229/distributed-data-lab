"""Actual report invariants plus counterexamples to the evidence validator."""

import copy, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_iceberg import validate


class IcebergEvidence(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / "results/iceberg.json").read_text())

    def test_actual_engine_evidence(self):
        self.assertTrue(validate(self.report)["valid"])

    def test_false_success_mutations_rejected(self):
        mutations = [
            lambda r: r["counterexample"].__setitem__(
                "naive_directory_ids", [1, 2, 3, 4, 5, 6]
            ),
            lambda r: r["schema_evolution"].__setitem__(
                "data_snapshot_id_after", "a-new-snapshot"
            ),
            lambda r: r["time_travel"]["current_rows"][0].__setitem__("quality", 99),
            lambda r: r["time_travel"]["base_rows_after_later_commits"].append(
                {"id": 999}
            ),
            lambda r: r["metadata_validation"][
                "original_data_file_hashes_after"
            ].__setitem__(
                next(iter(r["metadata_validation"]["original_data_file_hashes_after"])),
                "changed",
            ),
        ]
        for mutation in mutations:
            r = copy.deepcopy(self.report)
            mutation(r)
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(
                ValueError
            ):
                validate(r)


if __name__ == "__main__":
    unittest.main()
