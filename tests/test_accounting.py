import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from mcc.accounting import FIELDS, normalize, strict_object

ROOT = Path(__file__).resolve().parents[1]

class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT / "examples/accounting.json").read_text())

    def test_replay_transition_and_unknown(self):
        result = normalize(self.doc)
        self.assertEqual((result["unique_turns"], result["duplicate_replays"]), (3, 1))
        self.assertEqual(result["source"]["total"], 210)
        self.assertEqual({g["effective_model"] for g in result["groups"]}, {None, "example-model-a", "example-model-b"})
        self.assertIsNone(result["source"]["cached_input"])
        self.assertTrue(result["publication_eligible"])

    def test_conflict_fails_closed(self):
        self.doc["events"][1]["selected_model"] = "example-model-b"
        with self.assertRaises(ValueError): normalize(self.doc)

    def test_partition_every_field_and_model(self):
        for e in self.doc["events"]:
            e["usage"]["cached_input"] = 0
            e["usage"]["reasoning_output"] = 0
        result = normalize(self.doc)
        for field in FIELDS:
            self.assertEqual(result["source"][field], result["assigned"][field] + result["unresolved"][field])
            self.assertEqual(result["source"][field], sum(g["usage"][field] for g in result["groups"]))

    def test_partial_or_low_coverage_not_publishable(self):
        self.doc["source_complete"] = False
        self.assertFalse(normalize(self.doc)["publication_eligible"])
        self.doc["source_complete"] = True
        self.assertFalse(normalize(self.doc, 0.99)["publication_eligible"])

    def test_zero_and_unknown_denominator(self):
        self.doc["events"] = []
        self.assertIsNone(normalize(self.doc)["coverage"])
        self.assertFalse(normalize(self.doc)["publication_eligible"])

    def test_subset_total_and_boolean_rejected(self):
        for field, value in (("cached_input", 81), ("reasoning_output", 21), ("total", 101), ("input", True)):
            doc = copy.deepcopy(self.doc)
            doc["events"][0]["usage"][field] = value
            with self.assertRaises(ValueError): normalize(doc)

    def test_cumulative_unknown_keys_and_versions_rejected(self):
        for key, value in (("accounting", "cumulative"), ("conversation", "not-allowed")):
            doc = copy.deepcopy(self.doc)
            doc["events"][0][key] = value
            with self.assertRaises(ValueError): normalize(doc)
        self.doc["schema_version"] = 2
        with self.assertRaises(ValueError): normalize(self.doc)

    def test_explicit_binding_required(self):
        self.doc["events"][0]["binding"] = {"project": "example-project"}
        with self.assertRaises(ValueError): normalize(self.doc)

    def test_duplicate_json_key_and_policy_rejected(self):
        with self.assertRaises(ValueError): json.loads('{"a":1,"a":2}', object_pairs_hook=strict_object)
        for policy in (-1, 2, float("nan"), True):
            with self.assertRaises(ValueError): normalize(self.doc, policy)

    def test_cli(self):
        run = subprocess.run([sys.executable, "-m", "mcc.accounting", "examples/accounting.json"], cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["unique_turns"], 3)

if __name__ == "__main__":
    unittest.main()
