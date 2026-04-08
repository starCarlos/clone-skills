from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATE_EXAMPLES_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "generate_example_bundles.py"


class ColleagueCloneExampleGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="colleague-clone-examples-")
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(GENERATE_EXAMPLES_SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_generate_examples_can_build_all_examples_into_temp_root(self) -> None:
        output_root = self.root / "examples"
        proc = self.run_cmd("--output-root", str(output_root), "--validate")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["generated_count"], 6)
        self.assertTrue((output_root / "sample_search_api_predecessor" / "SKILL.md").exists())
        self.assertTrue((output_root / "sample_slack_reviewer" / "SKILL.md").exists())
        self.assertTrue((output_root / "sample_feishu_reviewer" / "SKILL.md").exists())
        self.assertTrue((output_root / "sample_dingtalk_reviewer" / "SKILL.md").exists())
        self.assertTrue((output_root / "sample_wechat_reviewer" / "SKILL.md").exists())
        self.assertTrue((output_root / "sample_pdf_image_reviewer" / "SKILL.md").exists())
        self.assertTrue((output_root / "sample_search_api_predecessor" / "analysis" / "runtime_contract.json").exists())
        self.assertTrue((output_root / "sample_search_api_predecessor" / "analysis" / "runtime_portraits.json").exists())
        generated_skill = (output_root / "sample_search_api_predecessor" / "SKILL.md").read_text(encoding="utf-8")
        runtime_contract = json.loads(
            (output_root / "sample_search_api_predecessor" / "analysis" / "runtime_contract.json").read_text(encoding="utf-8")
        )
        runtime_portraits = json.loads(
            (output_root / "sample_search_api_predecessor" / "analysis" / "runtime_portraits.json").read_text(encoding="utf-8")
        )
        self.assertIn("Role And Work Method", generated_skill)
        self.assertIn("Communication And Boundaries", generated_skill)
        self.assertIn("Runtime Portraits", generated_skill)
        self.assertIn("Professional Portrait", generated_skill)
        self.assertIn("Temperament Portrait", generated_skill)
        self.assertIn("Family Boundary Portrait", generated_skill)
        self.assertIn("Runtime Answer Strategy", generated_skill)
        self.assertIn("Runtime Boundaries", generated_skill)
        self.assertIn("Known Unknowns", generated_skill)
        self.assertIn("Refusal Pattern", generated_skill)
        self.assertEqual(runtime_contract["contract_scope"], "bounded_work_proxy")
        self.assertEqual(runtime_portraits["contract_scope"], "bounded_work_proxy")
        self.assertIn("runtime_portraits_summary", report["generated"][0]["validate"])
        self.assertIn("professional_portrait", report["generated"][0]["validate"]["runtime_portraits_summary"])
        self.assertIn("temperament_portrait", report["generated"][0]["validate"]["runtime_portraits_summary"])
        self.assertIn("family_boundary_portrait", report["generated"][0]["validate"]["runtime_portraits_summary"])

    def test_generate_examples_can_check_repo_readme_links(self) -> None:
        proc = self.run_cmd("--check-readme-links")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertFalse(report["readme_failures"])


if __name__ == "__main__":
    unittest.main()
