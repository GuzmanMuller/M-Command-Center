import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from mcc.model import validate

REPO = Path(__file__).resolve().parents[1]

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "canonical"
        self.root.mkdir(mode=0o700)
        self.data = self.base / "data"
        self.config = self.base / "config"
        self.cli("mcc.cli", "--config-dir", self.config, "--data-dir", self.data, "init")
        self.snapshot = json.loads((REPO / "examples/openclaw-projects.json").read_text())
        self.save()
        self.cli("mcc.cli", "--config-dir", self.config, "--data-dir", self.data,
                 "import", "--root", self.root, "--file", "projects.json")
        self.token = (self.config / "auth-token").read_bytes()

    def cli(self, module, *args, success=True):
        result = subprocess.run([sys.executable, "-m", module, *map(str,args)],
                                capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def save(self):
        path = self.root / "projects.json"
        path.write_text(json.dumps(self.snapshot))
        path.chmod(0o600)

    def bridge(self, *args, success=True):
        return self.cli("mcc.bridge", "--root", self.root, "--file", "projects.json",
                        "--data-dir", self.data, *args, success=success)

    def review(self):
        return json.loads(self.bridge().stdout)

    def apply(self, review, success=True):
        return self.bridge("--expected-current", review["current_sha256"],
                           "--expected-source", review["source_sha256"], "--apply", success=success)

    def test_refresh_backup_restore_idempotence_and_auth(self):
        before = (self.data / "snapshot.json").read_bytes()
        self.snapshot["projects"][0]["next_step"] = "Owner review of verified calendar"
        self.snapshot["projects"][0]["roadmap"].append("Verified: synthetic calendar test passed; 2026-01-02")
        self.save()
        review = self.review()
        self.assertTrue(review["changed"])
        self.assertEqual((self.data / "snapshot.json").read_bytes(), before)
        self.apply(review)
        self.assertEqual(json.loads((self.data / "snapshot.json").read_text()), self.snapshot)
        backup = self.data / ("snapshot-" + hashlib.sha256(before).hexdigest() + ".backup.json")
        self.assertEqual(backup.read_bytes(), before)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.data / "snapshot.json").stat().st_mode & 0o777, 0o600)
        self.assertFalse(json.loads(self.apply(self.review()).stdout)["changed"])
        self.cli("mcc.cli", "--config-dir", self.config, "--data-dir", self.data,
                 "import", "--root", self.data, "--file", backup.name)
        self.assertEqual(json.loads((self.data / "snapshot.json").read_text()), json.loads(before))
        self.assertEqual((self.config / "auth-token").read_bytes(), self.token)

    def test_missing_and_stale_digests(self):
        review = self.review()
        self.bridge("--apply", success=False)
        self.snapshot["projects"][0]["next_step"] = "changed after review"
        self.save()
        self.apply(review, success=False)
        review = self.review()
        (self.data / "snapshot.json").write_text(json.dumps({"schema_version":1,"projects":[]}))
        self.apply(review, success=False)
        self.assertFalse((self.data / "bridge.lock").exists())

    def test_identity_and_schema_denied(self):
        self.snapshot["projects"][0]["id"] = "other"
        self.save()
        self.bridge(success=False)
        self.snapshot["secret"] = "not a neutral field"
        self.save()
        self.bridge(success=False)

    def test_paths_permissions_and_lock_denied(self):
        for name in ["../canonical/projects.json", str(self.root / "projects.json")]:
            self.cli("mcc.bridge", "--root", self.root, "--file", name, success=False)
        (self.root / "alias.json").symlink_to(self.root / "projects.json")
        self.cli("mcc.bridge", "--root", self.root, "--file", "alias.json", success=False)
        alias = self.base / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        self.cli("mcc.bridge", "--root", alias, "--file", "projects.json", success=False)
        (self.root / "projects.json").chmod(0o644)
        self.bridge(success=False)
        self.save()
        self.root.chmod(0o755)
        self.bridge(success=False)
        self.root.chmod(0o700)
        (self.data / "bridge.lock").write_text("existing writer")
        self.apply(self.review(), success=False)
        self.assertEqual((self.data / "bridge.lock").read_text(), "existing writer")

class OnboardingTests(unittest.TestCase):
    def test_contract_and_instruction_links(self):
        validate(json.loads((REPO / "examples/openclaw-projects.json").read_text()))
        snippet = (REPO / "onboarding/AGENTS.snippet.md").read_text()
        for name in ["INSTRUCTIONS_FILE", "PROJECT_ROOT", "DATA_ROOT", "MCC_CLI", "BRIDGE_CLI"]:
            self.assertIn("{{" + name + "}}", snippet)
            snippet = snippet.replace("{{" + name + "}}", "/reviewed/" + name.lower())
        self.assertNotIn("{{", snippet)
        self.assertIn("MCC-INSTRUCTIONS.md", (REPO / "onboarding/skills/mcc-project-context/SKILL.md").read_text())
        self.assertTrue((REPO / "onboarding/MCC-INSTRUCTIONS.md").is_file())
        doc = (REPO / "docs/openclaw.md").read_text()
        self.assertNotIn(chr(0), doc)
        self.assertIn("--expected-source", doc)
        self.assertIn("not a Gateway plugin", doc)

if __name__ == "__main__":
    unittest.main()
