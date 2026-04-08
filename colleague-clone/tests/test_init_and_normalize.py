from __future__ import annotations

import json
import mailbox
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[2]
INIT_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "init_colleague_intake.py"
NORMALIZE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "normalize_colleague_sources.py"
PERSONA_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "analyze_colleague_persona.py"
WORK_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "analyze_colleague_work.py"
BUILD_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "build_colleague_skill.py"
VALIDATE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "validate_colleague_skill.py"
UPDATE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "update_colleague_skill.py"
ROLLBACK_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "rollback_colleague_skill.py"
BOOTSTRAP_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "bootstrap_colleague_clone.py"
PROMOTE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "promote_colleague_skill.py"
COMPARE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "compare_colleague_release.py"
INSPECT_RELEASE_BUNDLE_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "inspect_colleague_release_bundle.py"
EXPORT_RUNTIME_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "export_colleague_runtime.py"
SMOKE_RUNTIME_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "run_colleague_runtime_smoke.py"
RELEASE_HEALTH_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "run_colleague_release_health.py"
PROMPT_EVAL_SCRIPT = REPO_ROOT / "colleague-clone" / "scripts" / "run_colleague_prompt_eval.py"
FIXTURES_DIR = REPO_ROOT / "colleague-clone" / "tests" / "fixtures"


class ColleagueCloneCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="colleague-clone-tests-")
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cmd(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(script), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def write_minimal_pdf(self, path: Path, text: str) -> None:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        objects = [
            "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        ]
        stream = f"BT\n/F1 14 Tf\n36 96 Td\n({escaped}) Tj\nET\n"
        objects.append(f"4 0 obj\n<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}endstream\nendobj\n")
        objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

        pdf = "%PDF-1.4\n"
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf.encode("utf-8")))
            pdf += obj
        xref_offset = len(pdf.encode("utf-8"))
        pdf += f"xref\n0 {len(offsets)}\n"
        pdf += "0000000000 65535 f \n"
        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n"
        pdf += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
        path.write_bytes(pdf.encode("utf-8"))

    def write_minimal_image(self, path: Path, text: str) -> None:
        image = Image.new("RGB", (320, 120), "white")
        draw = ImageDraw.Draw(image)
        draw.text((12, 40), text, fill="black")
        image.save(path)

    def write_mock_prompt_eval_model(self, path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "from __future__ import annotations",
                    "",
                    "import json",
                    "import sys",
                    "",
                    "payload = json.load(sys.stdin)",
                    "case = payload.get('case', {}) if isinstance(payload.get('case', {}), dict) else {}",
                    "runtime_package = payload.get('runtime_package', {}) if isinstance(payload.get('runtime_package', {}), dict) else {}",
                    "system_prompt = runtime_package.get('system_prompt', {}) if isinstance(runtime_package.get('system_prompt', {}), dict) else {}",
                    "answer_style = system_prompt.get('answer_style', {}) if isinstance(system_prompt.get('answer_style', {}), dict) else {}",
                    "refusal_pattern = system_prompt.get('refusal_pattern', {}) if isinstance(system_prompt.get('refusal_pattern', {}), dict) else {}",
                    "default_modules = list(answer_style.get('default_modules', []))",
                    "default_review_focus = list(answer_style.get('default_review_focus', []))",
                    "workflow_sequence = list(answer_style.get('workflow_sequence', []))",
                    "delivery_preferences = list(answer_style.get('delivery_preferences', []))",
                    "interaction_tendencies = list(answer_style.get('interaction_tendencies', []))",
                    "known_unknowns = list(system_prompt.get('known_unknowns', []))",
                    "redirect_topics = list(refusal_pattern.get('redirect_to', []))",
                    "refusal_say = str(refusal_pattern.get('say', '')).strip()",
                    "disagreement_style = str(answer_style.get('disagreement_style', '')).strip() or 'work-focused'",
                    "prompt = str(case.get('prompt', '')).lower()",
                    "review_focus_text = ', '.join(default_review_focus) or 'review safety'",
                    "module_text = ', '.join(default_modules[:3]) or 'current work scope'",
                    "workflow_text = ', '.join(workflow_sequence[:3]) or 'clarify scope'",
                    "redirect_text = ', '.join(redirect_topics[:3]) or 'role scope'",
                    "uncertainty_text = known_unknowns[0] if known_unknowns else 'I do not have enough evidence to answer that precisely.'",
                    "delivery_text = ', '.join(delivery_preferences[:3]) or 'conclusion_first'",
                    "tendency_text = ', '.join(interaction_tendencies[:3]) or 'work-focused'",
                    "if 'family' in prompt or 'health' in prompt or 'finances' in prompt:",
                    "    answer = f\"{refusal_say} Ask instead about {redirect_text}.\"",
                    "elif 'limited evidence' in prompt or 'evidence' in prompt:",
                    "    answer = f\"Evidence note: {uncertainty_text}\"",
                    "elif 'unclear request' in prompt:",
                    "    answer = (",
                    "        f\"Question first: I would clarify context before disagreeing in a {disagreement_style} way. \"",
                    "        f\"Delivery style: {delivery_text}. Tendencies: {tendency_text}.\"",
                    "    )",
                    "else:",
                    "    answer = f\"Conclusion first: I would review {review_focus_text} in {module_text}. I would start by {workflow_text}.\"",
                    "print(json.dumps({'answer': answer}, ensure_ascii=False))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def write_bland_prompt_eval_model(self, path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "from __future__ import annotations",
                    "",
                    "import json",
                    "import sys",
                    "",
                    "_ = json.load(sys.stdin)",
                    "print(json.dumps({'answer': 'I would handle it carefully.'}, ensure_ascii=False))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

    def test_init_creates_bundle_structure_and_manifest(self) -> None:
        bundle_dir = self.root / "alice-bundle"
        source_path = self.root / "handoff.md"
        source_path.write_text("# Handoff\n\nKey notes\n", encoding="utf-8")

        proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Alice Example",
            "--relationship",
            "predecessor",
            "--source",
            str(source_path),
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["slug"], "alice-example")
        self.assertEqual(payload["state"], "sources_pending")
        self.assertTrue((bundle_dir / "sources" / "intake_request.yaml").exists())
        self.assertTrue((bundle_dir / "sources" / "manifest.jsonl").exists())
        self.assertTrue((bundle_dir / "normalized" / "docs").exists())

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["relationship"], "predecessor")
        self.assertEqual(meta["state"], "sources_pending")

    def test_normalize_converts_markdown_and_text_sources(self) -> None:
        bundle_dir = self.root / "bundle"
        markdown_path = self.root / "handoff.md"
        text_path = self.root / "notes.txt"
        markdown_path.write_text("# Handoff Notes\n\nAPI ownership\n", encoding="utf-8")
        text_path.write_text("Incident checklist\n\nEscalate DB issues\n", encoding="utf-8")

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Teammate",
            "--source",
            str(markdown_path),
            "--source",
            str(text_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(
            NORMALIZE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--strict",
        )
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)
        payload = json.loads(normalize_proc.stdout)
        self.assertEqual(payload["normalized_count"], 2)
        self.assertEqual(payload["state"], "sources_normalized")

        manifest_lines = [
            json.loads(line)
            for line in (bundle_dir / "sources" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(all(item["parse_status"] == "normalized" for item in manifest_lines))

        first_normalized = json.loads(
            (bundle_dir / "normalized" / "docs" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()[0]
        )
        self.assertEqual(first_normalized["title"], "Handoff Notes")
        self.assertEqual(first_normalized["privacy_scope"], "private_workspace")

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["state"], "sources_normalized")

    def test_end_to_end_pipeline_generates_draft_skill(self) -> None:
        bundle_dir = self.root / "pipeline"
        markdown_path = self.root / "handoff.md"
        text_path = self.root / "notes.txt"
        markdown_path.write_text(
            "\n".join(
                [
                    "# Search API Handoff",
                    "",
                    "负责 search-api 模块和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "CR重点：幂等、事务、N+1、错误码。",
                    "先写风险，再给方案，不要直接开工。",
                    "同步前先确认 owner。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        text_path.write_text(
            "\n".join(
                [
                    "结论前置，列表化回复。",
                    "紧急事故先止血，必要时回滚。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (
                INIT_SCRIPT,
                [
                    "--bundle-dir",
                    str(bundle_dir),
                    "--name",
                    "Search Teammate",
                    "--relationship",
                    "predecessor",
                    "--source",
                    str(markdown_path),
                    "--source",
                    str(text_path),
                ],
            ),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        validate_report = json.loads(validate_proc.stdout)
        self.assertTrue(validate_report["ok"])
        self.assertGreater(validate_report["evidence_count"], 0)
        self.assertIn("runtime_contract_summary", validate_report)
        self.assertIn("runtime_portraits", validate_report)
        self.assertIn("runtime_portraits_summary", validate_report)

        persona_md = (bundle_dir / "persona.md").read_text(encoding="utf-8")
        work_md = (bundle_dir / "work.md").read_text(encoding="utf-8")
        skill_md = (bundle_dir / "SKILL.md").read_text(encoding="utf-8")
        runtime_contract = json.loads((bundle_dir / "analysis" / "runtime_contract.json").read_text(encoding="utf-8"))
        runtime_portraits = json.loads((bundle_dir / "analysis" / "runtime_portraits.json").read_text(encoding="utf-8"))

        self.assertIn("Communication Style", persona_md)
        self.assertIn("Temperament Profile", persona_md)
        self.assertIn("Family Boundary", persona_md)
        self.assertIn("question-first", persona_md)
        self.assertIn("refuse_and_redirect", persona_md)
        self.assertIn("Professional Profile", work_md)
        self.assertIn("Role Scope", work_md)
        self.assertIn("幂等", work_md)
        self.assertIn("Communication And Boundaries", skill_md)
        self.assertIn("Runtime Portraits", skill_md)
        self.assertIn("Professional Portrait", skill_md)
        self.assertIn("Temperament Portrait", skill_md)
        self.assertIn("Family Boundary Portrait", skill_md)
        self.assertIn("Runtime Answer Strategy", skill_md)
        self.assertIn("Runtime Boundaries", skill_md)
        self.assertIn("Known Unknowns", skill_md)
        self.assertIn("Critical uncertainty: persona.collaboration_style", skill_md)
        self.assertIn("Critical uncertainty: work.workflow_patterns", skill_md)
        self.assertNotIn("Minor sparse signal:", skill_md)
        self.assertIn("Refuse to guess family relationships", skill_md)
        self.assertIn("Search Teammate", skill_md)
        self.assertIn("refuse_and_redirect", skill_md)
        self.assertEqual(runtime_contract["contract_scope"], "bounded_work_proxy")
        self.assertEqual(runtime_portraits["contract_scope"], "bounded_work_proxy")
        self.assertEqual(runtime_portraits["family_boundary_portrait"]["policy"], "refuse_and_redirect")
        self.assertEqual(runtime_portraits["answer_strategy"]["boundary_policy"], "refuse_and_redirect")
        self.assertEqual(validate_report["runtime_portraits_summary"]["boundary_policy"], "refuse_and_redirect")
        self.assertEqual(
            validate_report["runtime_portraits_summary"]["professional_portrait"]["summary"],
            runtime_portraits["professional_portrait"]["summary"],
        )
        self.assertEqual(
            validate_report["runtime_portraits_summary"]["temperament_portrait"]["questioning_tendency"],
            runtime_portraits["temperament_portrait"]["questioning_tendency"],
        )
        self.assertEqual(
            validate_report["runtime_portraits_summary"]["family_boundary_portrait"]["policy"],
            runtime_portraits["family_boundary_portrait"]["policy"],
        )
        self.assertIn("search-api", validate_report["runtime_portraits_summary"]["default_modules"])
        self.assertEqual(runtime_contract["refusal_pattern"]["redirect_to"][0], "role scope")
        self.assertTrue(runtime_contract["known_unknowns"]["required_items"])
        self.assertIn("runtime_contract_json", json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))["rendered_files"])
        self.assertIn("runtime_portraits_json", json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))["rendered_files"])
        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["state"], "draft_generated")

    def test_analysis_extracts_workflow_delivery_and_boundary_patterns(self) -> None:
        bundle_dir = self.root / "analysis-quality"
        source_path = self.root / "analysis.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Reviewer Notes",
                    "",
                    "负责 search-api 和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案，最后列执行 checklist。",
                    "CR重点：幂等、事务、N+1、错误码、兼容性。",
                    "结论前置，列表化回复。",
                    "紧急事故先止血，必要时回滚并升级。",
                    "不负责的模块不要直接改，先找 owner。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Quality User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        persona_profile = json.loads((bundle_dir / "analysis" / "persona_profile.json").read_text(encoding="utf-8"))
        work_profile = json.loads((bundle_dir / "analysis" / "work_profile.json").read_text(encoding="utf-8"))
        runtime_portraits = json.loads((bundle_dir / "analysis" / "runtime_portraits.json").read_text(encoding="utf-8"))

        self.assertEqual(persona_profile["collaboration_style"]["coordination_mode"], "owner-alignment")
        self.assertEqual(persona_profile["boundaries_and_taboos"]["boundary_mode"], "explicit")
        self.assertIn("rollback-first", persona_profile["stress_behaviors"]["response_mode"])
        self.assertEqual(persona_profile["semantic_view"]["collaboration_style"]["coordination_mode"], "owner-alignment")
        self.assertEqual(persona_profile["semantic_view"]["boundary_constraints"]["boundary_mode"], "explicit")
        self.assertIn("owner-aligned", persona_profile["semantic_view"]["temperament_profile"]["tendency_tags"])
        self.assertEqual(persona_profile["semantic_view"]["family_boundary_profile"]["policy"], "refuse_and_redirect")
        self.assertIn("role scope", persona_profile["semantic_view"]["family_boundary_profile"]["allowed_scope"])

        self.assertEqual(
            work_profile["workflow_patterns"]["operating_sequence"],
            ["clarify", "align_owner", "risk_first", "plan", "checklist"],
        )
        self.assertIn("conclusion_first", work_profile["delivery_preferences"]["format_preferences"])
        self.assertIn("list", work_profile["delivery_preferences"]["format_preferences"])
        self.assertIn("兼容性", work_profile["review_preferences"]["focus_areas"])
        self.assertEqual(
            work_profile["semantic_view"]["work_method"]["operating_sequence"],
            ["clarify", "align_owner", "risk_first", "plan", "checklist"],
        )
        self.assertIn("兼容性", work_profile["semantic_view"]["review_and_delivery"]["focus_areas"])
        self.assertEqual(
            work_profile["semantic_view"]["professional_profile"]["operating_sequence"],
            ["clarify", "align_owner", "risk_first", "plan", "checklist"],
        )
        self.assertIn("兼容性", work_profile["semantic_view"]["professional_profile"]["review_focus_areas"])
        self.assertEqual(
            runtime_portraits["answer_strategy"]["workflow_sequence"],
            ["clarify", "align_owner", "risk_first", "plan", "checklist"],
        )
        self.assertIn("owner-aligned", runtime_portraits["answer_strategy"]["interaction_tendencies"])
        self.assertEqual(runtime_portraits["family_boundary_portrait"]["policy"], "refuse_and_redirect")
        self.assertIn("role scope", runtime_portraits["family_boundary_portrait"]["redirect_topics"])

        evidence_index = [
            json.loads(line)
            for line in (bundle_dir / "evidence_index.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(any(item["field_path"] == "persona.stress_behaviors" for item in evidence_index))
        self.assertTrue(any(item["field_path"] == "work.explicit_rules" for item in evidence_index))

    def test_analysis_reports_conflicts_and_low_confidence_when_signals_clash(self) -> None:
        bundle_dir = self.root / "analysis-conflicts"
        source_path = self.root / "conflicts.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Conflict Notes",
                    "",
                    "遇到需求不清先问 context 和 impact。",
                    "不要反复追问，直接给结论并推进。",
                    "先确认 owner，再同步相关方。",
                    "不等对齐，直接开工，后面再补说明。",
                    "先写风险，再给方案。",
                    "直接开工，不用先列风险。",
                    "CR重点：幂等、事务。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Conflict User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        persona_profile = json.loads((bundle_dir / "analysis" / "persona_profile.json").read_text(encoding="utf-8"))
        work_profile = json.loads((bundle_dir / "analysis" / "work_profile.json").read_text(encoding="utf-8"))

        self.assertTrue(persona_profile["conflicts"])
        self.assertTrue(work_profile["conflicts"])
        self.assertLess(persona_profile["decision_patterns"]["confidence"], 0.7)
        self.assertLess(work_profile["workflow_patterns"]["confidence"], 0.7)
        self.assertIn("conflicting", persona_profile["decision_patterns"]["confidence_reason"])
        self.assertIn("conflicting", work_profile["workflow_patterns"]["confidence_reason"])

    def test_runtime_known_unknowns_surface_low_confidence_and_conflicts(self) -> None:
        bundle_dir = self.root / "runtime-known-unknowns"
        source_path = self.root / "runtime-conflicts.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Conflicts",
                    "",
                    "遇到需求不清先问 context 和 impact。",
                    "不要反复追问，直接给结论并推进。",
                    "先确认 owner，再同步相关方。",
                    "不等对齐，直接开工，后面再补说明。",
                    "先写风险，再给方案。",
                    "直接开工，不用先列风险。",
                    "CR重点：幂等、事务。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Runtime User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        skill_md = (bundle_dir / "SKILL.md").read_text(encoding="utf-8")
        runtime_contract = json.loads((bundle_dir / "analysis" / "runtime_contract.json").read_text(encoding="utf-8"))
        self.assertIn("Known Unknowns", skill_md)
        self.assertIn("Critical uncertainty: persona.decision_patterns", skill_md)
        self.assertIn("Critical uncertainty: work.workflow_patterns", skill_md)
        self.assertNotIn("Minor sparse signal:", skill_md)
        self.assertTrue(runtime_contract["known_unknowns"]["required_items"])
        self.assertTrue(runtime_contract["known_unknowns"]["minor_items"])

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["portrait_issues"])
        self.assertFalse(report["runtime_contract_issues"])
        self.assertTrue(report["runtime_required_caveats"])
        self.assertTrue(report["runtime_low_confidence_fields"])

    def test_analysis_excludes_private_sensitive_content_from_default_outputs(self) -> None:
        bundle_dir = self.root / "privacy-boundary"
        source_path = self.root / "privacy-mixed.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Mixed Notes",
                    "",
                    "负责 search-api 模块和 review 流程。",
                    "先确认 owner，再同步相关方。",
                    "孩子这周发烧，需要去医院。",
                    "家里房贷压力比较大。",
                    "CR重点：错误码和回滚预案。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Privacy User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        persona_profile = json.loads((bundle_dir / "analysis" / "persona_profile.json").read_text(encoding="utf-8"))
        work_profile = json.loads((bundle_dir / "analysis" / "work_profile.json").read_text(encoding="utf-8"))
        persona_md = (bundle_dir / "persona.md").read_text(encoding="utf-8")
        work_md = (bundle_dir / "work.md").read_text(encoding="utf-8")

        self.assertEqual(persona_profile["privacy_filter"]["counts"]["work_adjacent"], 1)
        self.assertEqual(work_profile["privacy_filter"]["counts"]["work_adjacent"], 1)
        self.assertIn("search-api", work_md)
        self.assertNotIn("发烧", persona_md)
        self.assertNotIn("房贷", work_md)
        skill_md = (bundle_dir / "SKILL.md").read_text(encoding="utf-8")
        runtime_contract = json.loads((bundle_dir / "analysis" / "runtime_contract.json").read_text(encoding="utf-8"))
        self.assertIn("Privacy note: some source material contained private-sensitive content", skill_md)
        self.assertIn("Known Unknowns", skill_md)
        self.assertIn("Privacy-limited area:", skill_md)
        self.assertTrue(runtime_contract["privacy_note_required"])
        self.assertIn("Privacy-limited area:", runtime_contract["known_unknowns"]["rendered"][0])
        self.assertTrue(runtime_contract["refusal_pattern"]["redirect_to"])

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        validate_report = json.loads(validate_proc.stdout)
        self.assertIn("private-sensitive content was excluded from default analysis", validate_report["privacy_issues"])

    def test_runtime_known_unknowns_omit_minor_sparse_fields(self) -> None:
        bundle_dir = self.root / "runtime-minor-sparse"
        source_path = self.root / "runtime-minor-sparse.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Minor Sparse",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先列风险，再给方案。",
                    "CR重点：幂等、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Minor Sparse User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        skill_md = (bundle_dir / "SKILL.md").read_text(encoding="utf-8")
        runtime_contract = json.loads((bundle_dir / "analysis" / "runtime_contract.json").read_text(encoding="utf-8"))
        self.assertIn("No major runtime caveats detected in the current bundle.", skill_md)
        self.assertNotIn("persona.collaboration_style", skill_md)
        self.assertNotIn("persona.boundaries_and_taboos", skill_md)
        self.assertNotIn("Minor sparse signal:", skill_md)
        self.assertFalse(runtime_contract["known_unknowns"]["required_items"])
        self.assertTrue(runtime_contract["known_unknowns"]["minor_items"])

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["runtime_required_caveats"])
        self.assertTrue(report["runtime_minor_caveats"])

    def test_validate_rejects_draft_when_runtime_contract_omits_expected_caveat(self) -> None:
        bundle_dir = self.root / "runtime-contract-validation"
        source_path = self.root / "runtime-contract.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Contract",
                    "",
                    "遇到需求不清先问 context 和 impact。",
                    "不要反复追问，直接给结论。",
                    "先确认 owner，再同步相关方。",
                    "不等对齐，直接开工。",
                    "先写风险，再给方案。",
                    "直接开工，不用先列风险。",
                    "CR重点：幂等、事务、错误码。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Runtime Validator", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        skill_path = bundle_dir / "SKILL.md"
        broken_skill = skill_path.read_text(encoding="utf-8").replace("persona.decision_patterns", "persona.decision_pattern_hidden")
        skill_path.write_text(broken_skill, encoding="utf-8")

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn(
            "runtime contract is missing required caveat summary: Critical uncertainty: persona.decision_patterns - Conflicting signals between question-first clarification and push-forward directness.",
            report["runtime_contract_issues"],
        )

    def test_validate_rejects_draft_when_runtime_portrait_summary_drifts(self) -> None:
        bundle_dir = self.root / "runtime-portrait-validation"
        source_path = self.root / "runtime-portrait.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Portrait",
                    "",
                    "负责 search-api 和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案，最后列执行 checklist。",
                    "CR重点：幂等、兼容性、错误码。",
                    "不负责的模块不要直接改，先找 owner。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Runtime Portrait Validator", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        skill_path = bundle_dir / "SKILL.md"
        broken_skill = skill_path.read_text(encoding="utf-8").replace(
            "Question-first, owner-aware, and boundary-conscious in work interactions.",
            "Tempered runtime portrait hidden.",
        )
        skill_path.write_text(broken_skill, encoding="utf-8")

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("runtime portraits are missing temperament portrait summary", report["portrait_issues"])

    def test_validate_rejects_draft_when_runtime_portraits_json_drifts(self) -> None:
        bundle_dir = self.root / "runtime-portrait-json-validation"
        source_path = self.root / "runtime-portrait-json.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Portrait JSON",
                    "",
                    "负责 search-api 和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案，最后列执行 checklist。",
                    "CR重点：幂等、兼容性、错误码。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Runtime Portrait JSON Validator", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        portraits_path = bundle_dir / "analysis" / "runtime_portraits.json"
        runtime_portraits = json.loads(portraits_path.read_text(encoding="utf-8"))
        runtime_portraits["answer_strategy"]["boundary_policy"] = "hidden_policy"
        portraits_path.write_text(json.dumps(runtime_portraits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("runtime portraits JSON drifted from analysis: answer_strategy", report["portrait_issues"])

    def test_validate_rejects_draft_when_portrait_semantic_view_is_incomplete(self) -> None:
        bundle_dir = self.root / "runtime-portrait-semantic-validation"
        source_path = self.root / "runtime-portrait-semantic.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Portrait Semantic",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "CR重点：幂等、错误码。",
                    "紧急事故先止血，必要时回滚。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Semantic Portrait Validator", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        work_profile_path = bundle_dir / "analysis" / "work_profile.json"
        work_profile = json.loads(work_profile_path.read_text(encoding="utf-8"))
        del work_profile["semantic_view"]["professional_profile"]["confidence_reason"]
        work_profile_path.write_text(json.dumps(work_profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(VALIDATE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn(
            "portrait semantic view is missing field: work.semantic_view.professional_profile.confidence_reason",
            report["portrait_issues"],
        )

    def test_update_pipeline_adds_sources_and_manual_override(self) -> None:
        bundle_dir = self.root / "update-pipeline"
        original_path = self.root / "original.md"
        extra_path = self.root / "extra.md"
        original_path.write_text(
            "# Original\n\n负责 payment-api。先问 context。CR重点：幂等。\n",
            encoding="utf-8",
        )
        extra_path.write_text(
            "# Extra\n\n错误码和事务也要检查。\n",
            encoding="utf-8",
        )

        for script, extra in [
            (
                INIT_SCRIPT,
                ["--bundle-dir", str(bundle_dir), "--name", "Updater", "--source", str(original_path)],
            ),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(extra_path),
            "--override-scope",
            "persona",
            "--override-field",
            "persona.decision_patterns.disagreement_style",
            "--override-value",
            "always asks for impact first",
            "--override-reason",
            "user correction",
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)
        update_payload = json.loads(update_proc.stdout)
        self.assertEqual(update_payload["added_source_count"], 1)
        self.assertTrue(update_payload["applied_override"])
        self.assertFalse(update_payload["runtime_contract_changed"])

        work_md = (bundle_dir / "work.md").read_text(encoding="utf-8")
        persona_md = (bundle_dir / "persona.md").read_text(encoding="utf-8")
        self.assertIn("错误码", work_md)
        self.assertIn("always asks for impact first", persona_md)
        self.assertTrue(any(path.name == "v1" for path in (bundle_dir / "versions").iterdir()))
        self.assertTrue((bundle_dir / "version_history.jsonl").exists())

    def test_update_accepts_explicit_source_kind_for_platform_json(self) -> None:
        bundle_dir = self.root / "update-platform-bundle"
        original_path = self.root / "original.md"
        original_path.write_text(
            "# Original\n\n负责 payment-api。先问 context。CR重点：幂等。\n",
            encoding="utf-8",
        )
        feishu_path = FIXTURES_DIR / "feishu_export" / "messages.json"

        for script, extra in [
            (
                INIT_SCRIPT,
                ["--bundle-dir", str(bundle_dir), "--name", "Updater", "--source", str(original_path)],
            ),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(feishu_path),
            "--source-kind",
            "workspace_export",
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)
        update_payload = json.loads(update_proc.stdout)
        self.assertEqual(update_payload["added_source_count"], 1)
        self.assertEqual(update_payload["added_sources"][0]["source_type"], "workspace_export")
        self.assertEqual(update_payload["added_sources"][0]["detection_mode"], "explicit")

        manifest_lines = [
            json.loads(line)
            for line in (bundle_dir / "sources" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(manifest_lines[-1]["source_type"], "workspace_export")
        self.assertEqual(manifest_lines[-1]["detection_mode"], "explicit")
        self.assertEqual(manifest_lines[-1]["detected_platform"], "feishu")

    def test_pasted_text_source_normalizes_into_bundle(self) -> None:
        bundle_dir = self.root / "pasted-bundle"
        proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Pasted User",
            "--pasted-text",
            "负责 billing-api。先问 impact。CR重点：错误码。",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        normalize_proc = self.run_cmd(
            NORMALIZE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--strict",
        )
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        manifest_lines = [
            json.loads(line)
            for line in (bundle_dir / "sources" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(manifest_lines[0]["source_type"], "pasted_text")
        self.assertTrue((bundle_dir / "sources" / "pasted" / "src_001.txt").exists())
        self.assertTrue((bundle_dir / "normalized" / "pasted" / "src_001.jsonl").exists())

    def test_rollback_restores_previous_snapshot(self) -> None:
        bundle_dir = self.root / "rollback-bundle"
        original_path = self.root / "original.md"
        extra_path = self.root / "extra.md"
        original_path.write_text("# Original\n\n负责 payment-api。CR重点：幂等。\n", encoding="utf-8")
        extra_path.write_text("# Extra\n\n错误码和事务也要检查。\n", encoding="utf-8")

        for script, extra in [
            (
                INIT_SCRIPT,
                ["--bundle-dir", str(bundle_dir), "--name", "Rollback User", "--source", str(original_path)],
            ),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(extra_path),
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)
        updated_work = (bundle_dir / "work.md").read_text(encoding="utf-8")
        self.assertIn("错误码", updated_work)

        rollback_proc = self.run_cmd(
            ROLLBACK_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--version",
            "v1",
        )
        self.assertEqual(rollback_proc.returncode, 0, rollback_proc.stderr)
        rolled_back_work = (bundle_dir / "work.md").read_text(encoding="utf-8")
        self.assertIn("幂等", rolled_back_work)
        self.assertNotIn("错误码和事务也要检查", rolled_back_work)

    def test_json_export_normalizes_into_message_records(self) -> None:
        bundle_dir = self.root / "json-bundle"
        export_path = self.root / "messages.json"
        export_path.write_text(
            json.dumps(
                {
                    "messages": [
                        {
                            "sender": "alice",
                            "timestamp": "2026-04-07T10:00:00Z",
                            "channel": "review-room",
                            "text": "先看 impact，再看方案。",
                        },
                        {
                            "sender": "alice",
                            "timestamp": "2026-04-07T10:05:00Z",
                            "text": "错误码要统一。",
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Json User",
            "--source",
            str(export_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(
            NORMALIZE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--strict",
        )
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        lines = (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["speaker"], "alice")
        self.assertEqual(records[0]["content_type"], "message")
        self.assertEqual(records[0]["channel"], "review-room")

    def test_workspace_export_accepts_field_mapping_for_nonstandard_json(self) -> None:
        bundle_dir = self.root / "mapped-workspace-export"
        export_path = self.root / "wechat-like.json"
        export_path.write_text(
            json.dumps(
                {
                    "payload": {
                        "entries": [
                            {
                                "actor": "Mapped Reviewer",
                                "roomName": "Mapped Review Room",
                                "sentAt": "2026-04-07T11:00:00Z",
                                "body": {"text": "先看 impact，再给方案。"},
                            }
                        ]
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        field_mapping = json.dumps(
            {
                "platform": "wechat",
                "items": "payload.entries",
                "speaker": "actor",
                "channel": "roomName",
                "timestamp": "sentAt",
                "text": "body.text",
            },
            ensure_ascii=False,
        )

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Mapped User",
            "--source",
            str(export_path),
            "--source-kind",
            "workspace_export",
            "--field-map",
            field_mapping,
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)
        init_report = json.loads(init_proc.stdout)
        self.assertEqual(init_report["sources"][0]["field_mapping"]["platform"], "wechat")

        normalize_proc = self.run_cmd(NORMALIZE_SCRIPT, "--bundle-dir", str(bundle_dir), "--strict")
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)
        normalize_report = json.loads(normalize_proc.stdout)
        self.assertEqual(normalize_report["detected_platforms"]["wechat"], 1)
        self.assertEqual(normalize_report["normalized_sources"][0]["platform_detection_mode"], "platform_hint")

        manifest = [
            json.loads(line)
            for line in (bundle_dir / "sources" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(manifest[0]["field_mapping"]["items"], "payload.entries")
        self.assertEqual(manifest[0]["detected_platform"], "wechat")
        self.assertEqual(manifest[0]["platform_detection_mode"], "platform_hint")
        self.assertEqual(manifest[0]["field_coverage"]["channel"], 1.0)

        records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "messages" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_type"], "wechat_export")
        self.assertEqual(records[0]["speaker"], "Mapped Reviewer")
        self.assertEqual(records[0]["channel"], "Mapped Review Room")
        self.assertIn("先看 impact", records[0]["text"])

    def test_eml_and_mbox_normalize_into_email_records(self) -> None:
        bundle_dir = self.root / "email-bundle"
        eml_path = self.root / "one.eml"
        mbox_path = self.root / "many.mbox"
        eml_path.write_text(
            "\n".join(
                [
                    "From: alice@example.com",
                    "To: team@example.com",
                    "Subject: Handoff",
                    "Date: Mon, 07 Apr 2026 10:00:00 +0000",
                    "",
                    "Search API handoff.",
                    "先看风险，再执行。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        box = mailbox.mbox(mbox_path)
        message = mailbox.mboxMessage()
        message["From"] = "bob@example.com"
        message["To"] = "team@example.com"
        message["Subject"] = "Incident Notes"
        message["Date"] = "Mon, 07 Apr 2026 11:00:00 +0000"
        message.set_payload("Check error codes and transactions.")
        box.add(message)
        box.flush()
        box.close()

        init_proc = self.run_cmd(
            INIT_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Email User",
            "--source",
            str(eml_path),
            "--source",
            str(mbox_path),
        )
        self.assertEqual(init_proc.returncode, 0, init_proc.stderr)

        normalize_proc = self.run_cmd(
            NORMALIZE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--strict",
        )
        self.assertEqual(normalize_proc.returncode, 0, normalize_proc.stderr)

        eml_records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "emails" / "src_001.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        mbox_records = [
            json.loads(line)
            for line in (bundle_dir / "normalized" / "emails" / "src_002.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(eml_records[0]["content_type"], "email")
        self.assertIn("Handoff", eml_records[0]["title"])
        self.assertEqual(mbox_records[0]["content_type"], "email")
        self.assertIn("Incident Notes", mbox_records[0]["title"])

    def test_bootstrap_runs_local_pipeline_in_one_command(self) -> None:
        bundle_dir = self.root / "bootstrap-bundle"
        source_path = self.root / "bootstrap.md"
        source_path.write_text(
            "# Bootstrap\n\n负责 search-api。先问 context。CR重点：幂等、错误码。\n",
            encoding="utf-8",
        )

        proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Bootstrap User",
            "--source",
            str(source_path),
            "--pasted-text",
            "结论前置。",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["steps"]["validate"]["ok"])
        self.assertTrue((bundle_dir / "SKILL.md").exists())

    def test_bootstrap_accepts_pdf_and_image_inputs(self) -> None:
        bundle_dir = self.root / "pdf-image-bootstrap"
        pdf_path = self.root / "owner-review.pdf"
        image_path = self.root / "rollback-risk-screenshot.png"
        self.write_minimal_pdf(pdf_path, "Owner alignment, impact first, and error code review.")
        self.write_minimal_image(image_path, "rollback risk")

        proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Pdf Image User",
            "--source",
            str(pdf_path),
            "--source",
            str(image_path),
            "--pasted-text",
            "先确认 owner，再同步相关方。",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["steps"]["normalize"]["source_breakdown"]["pdf_document"], 1)
        self.assertEqual(payload["steps"]["normalize"]["source_breakdown"]["image_file"], 1)
        self.assertTrue((bundle_dir / "normalized" / "docs" / "src_001.jsonl").exists())
        self.assertTrue((bundle_dir / "normalized" / "images" / "src_002.jsonl").exists())

    def test_bootstrap_accepts_source_kind_for_platform_json(self) -> None:
        bundle_dir = self.root / "bootstrap-platform-bundle"
        source_path = FIXTURES_DIR / "feishu_export" / "messages.json"

        proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Bootstrap Platform User",
            "--source",
            str(source_path),
            "--source-kind",
            "workspace_export",
            "--pasted-text",
            "先确认 owner，再同步相关方。",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["steps"]["init"]["sources"][0]["source_type"], "workspace_export")
        self.assertEqual(payload["steps"]["normalize"]["detected_platforms"]["feishu"], 1)

    def test_bootstrap_can_run_preflight_and_stop_on_risky_sources(self) -> None:
        bundle_dir = self.root / "bootstrap-preflight-bundle"
        source_path = self.root / "empty.json"
        source_path.write_text("[]\n", encoding="utf-8")

        proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Preflight User",
            "--source",
            str(source_path),
            "--preflight",
            "--stop-on-risky-preflight",
        )
        self.assertNotEqual(proc.returncode, 0)
        report = json.loads(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["steps"]["preflight"]["sources"][0]["risk_level"], "risky")
        self.assertFalse((bundle_dir / "meta.json").exists())

    def test_promote_moves_bundle_to_final_when_quality_gate_passes(self) -> None:
        bundle_dir = self.root / "promote-bundle"
        source_path = self.root / "promote.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Promote",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "CR重点：幂等、事务、N+1、错误码。",
                    "先写风险，再给方案。",
                    "紧急事故先止血，必要时回滚。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Promote User",
            "--source",
            str(source_path),
            "--pasted-text",
            "结论前置，列表化回复。",
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(
            PROMOTE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
        )
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)
        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertTrue(report["ok"])
        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["state"], "final_confirmed")
        promote_payload = json.loads(promote_proc.stdout)
        self.assertEqual(promote_payload["runtime_contract_summary"]["final_issue_count"], 0)
        self.assertEqual(promote_payload["runtime_portraits_summary"]["boundary_policy"], "refuse_and_redirect")
        self.assertTrue(promote_payload["runtime_portraits_summary"]["default_review_focus"])
        self.assertEqual(promote_payload["runtime_release_decision"]["decision"], "allow")
        self.assertEqual(promote_payload["runtime_release_decision"]["reason_codes"], [])
        self.assertEqual(promote_payload["release_manifest"]["schema_version"], "colleague_clone_release_manifest/v1")
        self.assertEqual(promote_payload["release_manifest"]["bundle"]["state"], "final_confirmed")
        self.assertEqual(promote_payload["release_manifest"]["sources"]["source_count"], 2)
        self.assertEqual(promote_payload["release_manifest"]["runtime_release_decision"]["decision"], "allow")
        self.assertEqual(promote_payload["release_manifest"]["release_health"]["decision"]["decision"], "allow")
        self.assertFalse(promote_payload["release_manifest"]["release_health"]["compare"]["has_previous"])
        self.assertTrue(promote_payload["release_manifest"]["runtime_smoke_summary"]["ok"])
        self.assertEqual(promote_payload["release_manifest"]["runtime_prompt_eval_summary"]["decision"], "allow")
        self.assertEqual(promote_payload["release_manifest"]["runtime_prompt_eval_summary"]["score"], 100)
        self.assertEqual(
            promote_payload["release_manifest"]["runtime_portraits_summary"]["professional_portrait"]["summary"],
            promote_payload["runtime_portraits_summary"]["professional_portrait"]["summary"],
        )
        self.assertEqual(
            promote_payload["release_manifest"]["runtime_portraits_summary"]["family_boundary_portrait"]["policy"],
            "refuse_and_redirect",
        )
        self.assertFalse(promote_payload["release_compare_brief"]["has_previous"])
        self.assertFalse(promote_payload["release_compare_brief"]["changed"])
        self.assertEqual(promote_payload["runtime_package"]["schema_version"], "colleague_clone_runtime_package/v1")
        self.assertEqual(promote_payload["runtime_package"]["bundle"]["state"], "final_confirmed")
        self.assertEqual(promote_payload["runtime_package"]["release_health"]["decision"]["decision"], "allow")
        self.assertTrue(promote_payload["runtime_package"]["release_health"]["smoke"]["ok"])
        self.assertEqual(promote_payload["runtime_package"]["release_health"]["prompt_eval"]["decision"], "allow")
        self.assertTrue(promote_payload["runtime_package"]["runtime_smoke_summary"]["ok"])
        self.assertEqual(promote_payload["runtime_package"]["runtime_prompt_eval_summary"]["decision"], "allow")
        self.assertEqual(promote_payload["runtime_package"]["runtime_prompt_eval_summary"]["score"], 100)
        self.assertEqual(
            promote_payload["runtime_package"]["runtime_portraits_summary"]["temperament_portrait"]["disagreement_style"],
            promote_payload["runtime_portraits_summary"]["temperament_portrait"]["disagreement_style"],
        )
        self.assertEqual(
            promote_payload["runtime_package"]["runtime_portraits_summary"]["family_boundary_portrait"]["redirect_topics"][0],
            "role scope",
        )
        self.assertEqual(
            promote_payload["runtime_package"]["system_prompt"]["refusal_pattern"]["redirect_to"][0],
            "role scope",
        )
        self.assertEqual(promote_payload["runtime_smoke"]["schema_version"], "colleague_clone_runtime_smoke_artifact/v1")
        self.assertTrue(promote_payload["runtime_smoke"]["runtime_smoke_report"]["ok"])
        self.assertTrue(promote_payload["runtime_smoke"]["runtime_smoke_brief"]["ok"])
        self.assertFalse(promote_payload["runtime_smoke_compare_brief"]["has_previous"])
        self.assertEqual(promote_payload["runtime_release_health"]["schema_version"], "colleague_clone_runtime_release_health/v1")
        self.assertEqual(promote_payload["runtime_release_health"]["release_health"]["decision"]["decision"], "allow")
        self.assertTrue(promote_payload["runtime_release_health"]["release_health"]["smoke"]["ok"])
        self.assertEqual(promote_payload["runtime_release_health"]["release_health"]["prompt_eval"]["score"], 100)
        self.assertFalse(promote_payload["runtime_release_health_compare_brief"]["has_previous"])
        self.assertEqual(promote_payload["runtime_prompt_eval"]["schema_version"], "colleague_clone_runtime_prompt_eval_artifact/v1")
        self.assertTrue(promote_payload["runtime_prompt_eval"]["runtime_prompt_eval_report"]["ok"])
        self.assertEqual(promote_payload["runtime_prompt_eval"]["runtime_prompt_eval_brief"]["decision"], "allow")
        self.assertFalse(promote_payload["runtime_prompt_eval_compare_brief"]["has_previous"])
        self.assertTrue((bundle_dir / "release_manifest.json").exists())
        self.assertTrue((bundle_dir / "runtime_package.json").exists())
        self.assertTrue((bundle_dir / "runtime_smoke.json").exists())
        self.assertTrue((bundle_dir / "runtime_release_health.json").exists())
        self.assertTrue((bundle_dir / "runtime_prompt_eval.json").exists())

    def test_promote_rejects_runtime_contract_gate_before_finalizing(self) -> None:
        bundle_dir = self.root / "promote-runtime-gate"
        source_path = self.root / "promote-runtime-gate.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Promote Runtime Gate",
                    "",
                    "遇到需求不清先问 context 和 impact。",
                    "不要反复追问，直接给结论。",
                    "先确认 owner，再同步相关方。",
                    "不等对齐，直接开工。",
                    "先写风险，再给方案。",
                    "直接开工，不用先列风险。",
                    "CR重点：幂等、事务、错误码。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Promote Runtime Gate User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(
            PROMOTE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
        )
        self.assertNotEqual(promote_proc.returncode, 0)
        promote_report = json.loads(promote_proc.stdout)
        self.assertIn("runtime contract still contains unresolved conflicts", promote_report["runtime_contract_final_issues"])
        self.assertTrue(promote_report["runtime_contract_summary"]["has_required_caveats"])
        self.assertIn("boundary_policy", promote_report["runtime_portraits_summary"])
        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["state"], "draft_generated")

    def test_update_can_resolve_conflicts_and_restore_final_readiness(self) -> None:
        bundle_dir = self.root / "resolve-conflicts-bundle"
        source_path = self.root / "resolve-conflicts.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Resolve Conflicts",
                    "",
                    "遇到需求不清先问 context 和 impact。",
                    "不要反复追问，直接给结论。",
                    "先确认 owner，再同步相关方。",
                    "不等对齐，直接开工。",
                    "先写风险，再给方案。",
                    "直接开工，不用先列风险。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Resolve User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        first_update = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--resolve-conflict-scope",
            "persona",
            "--resolve-conflict-field",
            "persona.decision_patterns",
            "--resolve-conflict-note",
            "Prefer question-first over direct push",
            "--rebuild",
        )
        self.assertEqual(first_update.returncode, 0, first_update.stderr)

        second_update = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--resolve-conflict-scope",
            "work",
            "--resolve-conflict-field",
            "work.workflow_patterns",
            "--resolve-conflict-note",
            "Prefer risk-first planning over execution-first shortcuts",
            "--rebuild",
        )
        self.assertEqual(second_update.returncode, 0, second_update.stderr)

        third_update = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--resolve-conflict-scope",
            "persona",
            "--resolve-conflict-field",
            "persona.collaboration_style",
            "--resolve-conflict-note",
            "Prefer owner alignment over bypassing coordination",
            "--rebuild",
        )
        self.assertEqual(third_update.returncode, 0, third_update.stderr)

        persona_profile = json.loads((bundle_dir / "analysis" / "persona_profile.json").read_text(encoding="utf-8"))
        work_profile = json.loads((bundle_dir / "analysis" / "work_profile.json").read_text(encoding="utf-8"))
        self.assertFalse(any(item["field_path"] == "persona.decision_patterns" for item in persona_profile["conflicts"]))
        self.assertFalse(any(item["field_path"] == "persona.collaboration_style" for item in persona_profile["conflicts"]))
        self.assertFalse(any(item["field_path"] == "work.workflow_patterns" for item in work_profile["conflicts"]))
        self.assertEqual(
            [item["field_path"] for item in persona_profile["resolved_conflicts"]],
            ["persona.decision_patterns", "persona.collaboration_style"],
        )
        self.assertEqual(
            [item["field_path"] for item in work_profile["resolved_conflicts"]],
            ["work.workflow_patterns"],
        )
        self.assertIn("resolved by manual override", persona_profile["decision_patterns"]["confidence_reason"])
        self.assertIn("resolved by manual override", persona_profile["collaboration_style"]["confidence_reason"])
        self.assertIn("resolved by manual override", work_profile["workflow_patterns"]["confidence_reason"])
        self.assertEqual(len(persona_profile["resolution_history"]), 2)
        self.assertEqual(len(work_profile["resolution_history"]), 1)
        self.assertEqual(
            persona_profile["resolution_history"][0]["conflict_snapshot"]["field_path"],
            "persona.decision_patterns",
        )
        self.assertEqual(
            persona_profile["resolution_history"][1]["field_snapshot_before"]["confidence_reason"],
            "conflicting signals lower confidence",
        )

        promote_proc = self.run_cmd(
            PROMOTE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
        )
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)
        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertEqual(len(report["resolved_conflicts"]), 3)
        self.assertEqual(len(report["resolution_history"]), 3)
        self.assertTrue(report["release_manifest"])

    def test_promote_rejects_sparse_bundle(self) -> None:
        bundle_dir = self.root / "sparse-promote-bundle"
        source_path = self.root / "sparse.md"
        source_path.write_text("# Sparse\n\n负责 api。\n", encoding="utf-8")
        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Sparse User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(
            PROMOTE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
        )
        self.assertNotEqual(promote_proc.returncode, 0)

    def test_update_reports_runtime_contract_drift_when_rebuild_adds_privacy_limit(self) -> None:
        bundle_dir = self.root / "update-runtime-drift"
        original_path = self.root / "update-runtime-base.md"
        extra_path = self.root / "update-runtime-privacy.md"
        original_path.write_text(
            "# Base\n\n负责 payment-api。先问 context。CR重点：幂等。\n",
            encoding="utf-8",
        )
        extra_path.write_text(
            "\n".join(
                [
                    "# Privacy Shift",
                    "",
                    "负责 payment-api review。",
                    "孩子这周发烧，需要去医院。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (
                INIT_SCRIPT,
                ["--bundle-dir", str(bundle_dir), "--name", "Runtime Drift User", "--source", str(original_path)],
            ),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(extra_path),
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)
        update_payload = json.loads(update_proc.stdout)
        self.assertTrue(update_payload["runtime_contract_changed"])
        self.assertTrue(update_payload["runtime_portraits_changed"])
        self.assertTrue(update_payload["runtime_contract_drift"]["entered_required_caveat"])
        self.assertTrue(update_payload["runtime_contract_drift"]["entered_privacy_limited"])
        self.assertTrue(update_payload["runtime_contract_drift"]["after"]["privacy_limited"])
        self.assertTrue(update_payload["runtime_portraits_drift"]["private_signal_changed"])
        self.assertTrue(update_payload["runtime_portraits_drift"]["after"]["private_signal_present"])
        self.assertEqual(update_payload["runtime_release_review"]["status"], "pending_ack")
        self.assertEqual(update_payload["runtime_release_review"]["history"][0]["event"], "drift_detected")
        self.assertEqual(update_payload["runtime_release_review"]["drift_summary"]["severity"], "blocking")
        self.assertIn(
            "entered privacy-limited runtime boundary",
            update_payload["runtime_release_review"]["drift_summary"]["new_restrictions"],
        )
        self.assertIn(
            "runtime portrait entered private-signal state",
            update_payload["runtime_release_review"]["drift_summary"]["new_restrictions"],
        )
        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["runtime_release_review"]["status"], "pending_ack")
        self.assertTrue(meta["runtime_release_review"]["requires_ack"])
        self.assertEqual(len(meta["runtime_release_review"]["history"]), 1)

    def test_update_reports_runtime_portrait_only_drift_when_scope_changes(self) -> None:
        bundle_dir = self.root / "update-runtime-portrait-drift"
        original_path = self.root / "update-runtime-portrait-base.md"
        extra_path = self.root / "update-runtime-portrait-extra.md"
        original_path.write_text(
            "\n".join(
                [
                    "# Base Portrait",
                    "",
                    "负责 payment-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "CR重点：错误码。",
                    "先写风险，再给方案。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        extra_path.write_text(
            "\n".join(
                [
                    "# Scope Shift",
                    "",
                    "现在也负责 search-api review。",
                    "新增评审重点：兼容性。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (
                INIT_SCRIPT,
                ["--bundle-dir", str(bundle_dir), "--name", "Runtime Portrait Drift User", "--source", str(original_path)],
            ),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(extra_path),
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)
        update_payload = json.loads(update_proc.stdout)
        self.assertFalse(update_payload["runtime_contract_changed"])
        self.assertTrue(update_payload["runtime_portraits_changed"])
        self.assertTrue(update_payload["runtime_portraits_drift"]["added_default_modules"])
        self.assertTrue(update_payload["runtime_portraits_drift"]["added_review_focus"])
        self.assertEqual(update_payload["runtime_release_review"]["status"], "pending_ack")
        self.assertEqual(update_payload["runtime_release_review"]["drift_summary"]["severity"], "caution")
        self.assertIn(
            "runtime portrait default modules changed",
            update_payload["runtime_release_review"]["drift_summary"]["new_uncertainty"],
        )

    def test_promote_requires_runtime_drift_ack_before_finalizing(self) -> None:
        bundle_dir = self.root / "runtime-drift-ack-gate"
        base_path = self.root / "runtime-drift-ack-base.md"
        privacy_path = self.root / "runtime-drift-ack-privacy.md"
        base_path.write_text(
            "\n".join(
                [
                    "# Ack Gate Base",
                    "",
                    "负责 payment-api 模块和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                    "不负责的模块不要直接改，先找 owner。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        privacy_path.write_text(
            "\n".join(
                [
                    "# Ack Gate Privacy",
                    "",
                    "负责 payment-api review。",
                    "孩子这周发烧，需要去医院。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Ack Gate User",
            "--source",
            str(base_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        first_promote = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(first_promote.returncode, 0, first_promote.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(privacy_path),
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)
        update_payload = json.loads(update_proc.stdout)
        self.assertEqual(update_payload["runtime_release_review"]["status"], "pending_ack")

        blocked_promote = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertNotEqual(blocked_promote.returncode, 0)
        blocked_payload = json.loads(blocked_promote.stdout)
        self.assertIn(
            "runtime drift review is pending acknowledgement before final release",
            blocked_payload["runtime_release_review_issues"],
        )
        self.assertEqual(blocked_payload["runtime_release_decision"]["decision"], "block")
        self.assertIn("unacked_drift", blocked_payload["runtime_release_decision"]["reason_codes"])
        self.assertIn("privacy_boundary_shift", blocked_payload["runtime_release_decision"]["reason_codes"])
        self.assertIn("portrait_boundary_shift", blocked_payload["runtime_release_decision"]["reason_codes"])
        self.assertEqual(blocked_payload["runtime_release_review_brief"]["severity"], "blocking")
        self.assertIn("acknowledgement is required", blocked_payload["runtime_release_review_brief"]["headline"])
        self.assertTrue(blocked_payload["runtime_release_review_brief"]["items"])
        self.assertEqual(blocked_payload["runtime_portraits_review_brief"]["severity"], "blocking")
        self.assertTrue(blocked_payload["runtime_portraits_review_brief"]["items"])

        ack_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--ack-runtime-drift",
            "--ack-note",
            "Reviewed privacy-limited runtime shift for the new source.",
            "--ack-by",
            "qa-reviewer",
        )
        self.assertEqual(ack_proc.returncode, 0, ack_proc.stderr)
        ack_payload = json.loads(ack_proc.stdout)
        self.assertTrue(ack_payload["acknowledged_runtime_drift"])
        self.assertEqual(ack_payload["runtime_release_review"]["status"], "acknowledged")
        self.assertEqual(ack_payload["runtime_release_review"]["last_ack"]["acknowledged_by"], "qa-reviewer")
        self.assertTrue(ack_payload["runtime_release_review"]["last_ack_covers_latest_drift"])
        self.assertEqual(len(ack_payload["runtime_release_review"]["history"]), 2)
        self.assertEqual(ack_payload["runtime_release_review"]["history"][1]["event"], "drift_acknowledged")

        final_promote = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(final_promote.returncode, 0, final_promote.stderr)
        final_payload = json.loads(final_promote.stdout)
        self.assertEqual(final_payload["runtime_release_review"]["status"], "acknowledged")
        self.assertEqual(final_payload["runtime_release_decision"]["decision"], "caution")
        self.assertIn("acknowledged_runtime_drift", final_payload["runtime_release_decision"]["reason_codes"])

    def test_compare_release_reports_no_previous_release_after_first_promote(self) -> None:
        bundle_dir = self.root / "compare-first-release"
        source_path = self.root / "compare-first-release.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Compare First Release",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Compare First User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        compare_proc = self.run_cmd(COMPARE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(compare_proc.returncode, 0, compare_proc.stderr)
        compare_payload = json.loads(compare_proc.stdout)
        self.assertTrue(compare_payload["ok"])
        self.assertFalse(compare_payload["compare"]["has_previous"])
        self.assertFalse(compare_payload["compare"]["changed"])

    def test_compare_release_reports_changed_sections_after_second_promote(self) -> None:
        bundle_dir = self.root / "compare-second-release"
        source_path = self.root / "compare-second-release-base.md"
        extra_path = self.root / "compare-second-release-extra.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Compare Second Release",
                    "",
                    "负责 payment-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        extra_path.write_text(
            "\n".join(
                [
                    "# Compare Second Release Extra",
                    "",
                    "现在也负责 search-api review。",
                    "新增评审重点：兼容性。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Compare Second User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        first_promote = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(first_promote.returncode, 0, first_promote.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(extra_path),
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)

        ack_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--ack-runtime-drift",
            "--ack-note",
            "Reviewed scope expansion before second release.",
        )
        self.assertEqual(ack_proc.returncode, 0, ack_proc.stderr)

        second_promote = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(second_promote.returncode, 0, second_promote.stderr)
        second_payload = json.loads(second_promote.stdout)
        self.assertTrue(second_payload["release_compare_brief"]["has_previous"])
        self.assertTrue(second_payload["release_compare_brief"]["changed"])
        self.assertTrue(second_payload["runtime_release_health_compare_brief"]["has_previous"])
        self.assertTrue(second_payload["runtime_release_health_compare_brief"]["changed"])
        self.assertIn("runtime_portraits_summary", second_payload["release_compare_report"]["changed_sections"])
        self.assertIn("sources", second_payload["release_compare_report"]["changed_sections"])

        compare_proc = self.run_cmd(COMPARE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(compare_proc.returncode, 0, compare_proc.stderr)
        compare_payload = json.loads(compare_proc.stdout)
        self.assertTrue(compare_payload["compare"]["has_previous"])
        self.assertTrue(compare_payload["compare"]["changed"])
        self.assertIn("runtime_portraits_summary", compare_payload["compare"]["changed_sections"])
        self.assertIn("sources", compare_payload["compare"]["changed_sections"])

    def test_validate_require_final_reports_pending_runtime_drift_ack(self) -> None:
        bundle_dir = self.root / "runtime-drift-validate"
        base_path = self.root / "runtime-drift-validate-base.md"
        privacy_path = self.root / "runtime-drift-validate-privacy.md"
        base_path.write_text(
            "\n".join(
                [
                    "# Drift Validate Base",
                    "",
                    "负责 search-api 模块和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                    "不负责的模块不要直接改，先找 owner。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        privacy_path.write_text(
            "\n".join(
                [
                    "# Drift Validate Privacy",
                    "",
                    "负责 search-api review。",
                    "孩子这周发烧，需要去医院。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Drift User",
            "--source",
            str(base_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        update_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(privacy_path),
            "--rebuild",
        )
        self.assertEqual(update_proc.returncode, 0, update_proc.stderr)

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        meta["state"] = "final_confirmed"
        (bundle_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn(
            "runtime drift review is pending acknowledgement before final release",
            report["runtime_release_review_issues"],
        )
        self.assertIn(
            "runtime drift review is pending acknowledgement before final release",
            report["final_quality_issues"],
        )
        self.assertEqual(report["runtime_release_review"]["status"], "pending_ack")
        self.assertEqual(report["runtime_release_decision"]["decision"], "block")
        self.assertIn("unacked_drift", report["runtime_release_decision"]["reason_codes"])
        self.assertEqual(report["runtime_release_review_brief"]["severity"], "blocking")
        self.assertIn("acknowledgement is required", report["runtime_release_review_brief"]["headline"])
        self.assertEqual(report["runtime_portraits_review_brief"]["severity"], "blocking")

    def test_validate_require_final_reports_missing_release_manifest(self) -> None:
        bundle_dir = self.root / "missing-release-manifest"
        source_path = self.root / "missing-release-manifest.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Missing Release Manifest",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Missing Manifest User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        meta["state"] = "final_confirmed"
        (bundle_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn("release manifest is missing or invalid", report["release_manifest_issues"])
        self.assertIn("release manifest is missing or invalid", report["final_quality_issues"])

    def test_validate_require_final_reports_missing_runtime_package(self) -> None:
        bundle_dir = self.root / "missing-runtime-package"
        source_path = self.root / "missing-runtime-package.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Missing Runtime Package",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Missing Runtime Package User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)
        (bundle_dir / "runtime_package.json").unlink()

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn("runtime package is missing or invalid", report["runtime_package_issues"])
        self.assertIn("runtime package is missing or invalid", report["final_quality_issues"])

    def test_validate_rejects_drifted_release_manifest(self) -> None:
        bundle_dir = self.root / "drifted-release-manifest"
        source_path = self.root / "drifted-release-manifest.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Drifted Release Manifest",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Drifted Manifest User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(
            PROMOTE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
        )
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        release_manifest_path = bundle_dir / "release_manifest.json"
        release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
        release_manifest["runtime_portraits_summary"]["boundary_policy"] = "custom_override"
        release_manifest_path.write_text(json.dumps(release_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn("release manifest drifted from bundle: runtime_portraits_summary", report["release_manifest_issues"])
        self.assertIn("release manifest drifted from bundle: runtime_portraits_summary", report["final_quality_issues"])

    def test_validate_rejects_drifted_runtime_package(self) -> None:
        bundle_dir = self.root / "drifted-runtime-package"
        source_path = self.root / "drifted-runtime-package.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Drifted Runtime Package",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Drifted Runtime Package User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        runtime_package_path = bundle_dir / "runtime_package.json"
        runtime_package = json.loads(runtime_package_path.read_text(encoding="utf-8"))
        runtime_package["system_prompt"]["answer_style"]["boundary_policy"] = "custom_override"
        runtime_package_path.write_text(json.dumps(runtime_package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn("runtime package drifted from bundle: system_prompt", report["runtime_package_issues"])
        self.assertIn("runtime package drifted from bundle: system_prompt", report["final_quality_issues"])

    def test_validate_rejects_drifted_runtime_prompt_eval_artifact(self) -> None:
        bundle_dir = self.root / "drifted-runtime-prompt-eval"
        source_path = self.root / "drifted-runtime-prompt-eval.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Drifted Runtime Prompt Eval",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Drifted Runtime Prompt Eval User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        runtime_prompt_eval_path = bundle_dir / "runtime_prompt_eval.json"
        runtime_prompt_eval = json.loads(runtime_prompt_eval_path.read_text(encoding="utf-8"))
        runtime_prompt_eval["runtime_prompt_eval_brief"]["decision"] = "block"
        runtime_prompt_eval_path.write_text(json.dumps(runtime_prompt_eval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn(
            "runtime prompt eval artifact drifted from bundle: runtime_prompt_eval_brief",
            report["runtime_prompt_eval_artifact_issues"],
        )
        self.assertIn(
            "runtime prompt eval artifact drifted from bundle: runtime_prompt_eval_brief",
            report["final_quality_issues"],
        )

    def test_validate_rejects_drifted_runtime_smoke_artifact(self) -> None:
        bundle_dir = self.root / "drifted-runtime-smoke"
        source_path = self.root / "drifted-runtime-smoke.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Drifted Runtime Smoke",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Drifted Runtime Smoke User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        runtime_smoke_path = bundle_dir / "runtime_smoke.json"
        runtime_smoke = json.loads(runtime_smoke_path.read_text(encoding="utf-8"))
        runtime_smoke["runtime_smoke_brief"]["ok"] = False
        runtime_smoke_path.write_text(json.dumps(runtime_smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn(
            "runtime smoke artifact drifted from bundle: runtime_smoke_brief",
            report["runtime_smoke_artifact_issues"],
        )
        self.assertIn(
            "runtime smoke artifact drifted from bundle: runtime_smoke_brief",
            report["final_quality_issues"],
        )

    def test_validate_rejects_drifted_runtime_release_health_artifact(self) -> None:
        bundle_dir = self.root / "validate-drifted-runtime-release-health"
        source_path = self.root / "validate-drifted-runtime-release-health.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Drifted Runtime Release Health",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Drifted Runtime Release Health User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        runtime_release_health_path = bundle_dir / "runtime_release_health.json"
        runtime_release_health = json.loads(runtime_release_health_path.read_text(encoding="utf-8"))
        runtime_release_health["release_health"]["smoke"]["ok"] = False
        runtime_release_health_path.write_text(json.dumps(runtime_release_health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertIn(
            "runtime release health artifact drifted from bundle: release_health",
            report["runtime_release_health_artifact_issues"],
        )
        self.assertIn(
            "runtime release health artifact drifted from bundle: release_health",
            report["final_quality_issues"],
        )

    def test_export_runtime_package_regenerates_deleted_package(self) -> None:
        bundle_dir = self.root / "export-runtime-package"
        source_path = self.root / "export-runtime-package.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Export Runtime Package",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Export Runtime Package User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)
        runtime_package_path = bundle_dir / "runtime_package.json"
        runtime_smoke_path = bundle_dir / "runtime_smoke.json"
        runtime_release_health_path = bundle_dir / "runtime_release_health.json"
        runtime_prompt_eval_path = bundle_dir / "runtime_prompt_eval.json"
        runtime_package_path.unlink()
        runtime_smoke_path.unlink()
        runtime_release_health_path.unlink()
        runtime_prompt_eval_path.unlink()

        export_proc = self.run_cmd(EXPORT_RUNTIME_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(export_proc.returncode, 0, export_proc.stderr)
        export_payload = json.loads(export_proc.stdout)
        self.assertEqual(export_payload["runtime_package"]["schema_version"], "colleague_clone_runtime_package/v1")
        self.assertEqual(export_payload["runtime_package"]["release_health"]["decision"]["decision"], "allow")
        self.assertTrue(export_payload["runtime_package"]["runtime_smoke_summary"]["ok"])
        self.assertEqual(export_payload["runtime_smoke"]["schema_version"], "colleague_clone_runtime_smoke_artifact/v1")
        self.assertTrue(export_payload["runtime_smoke"]["runtime_smoke_brief"]["ok"])
        self.assertEqual(export_payload["runtime_release_health"]["schema_version"], "colleague_clone_runtime_release_health/v1")
        self.assertTrue(export_payload["runtime_release_health"]["release_health"]["smoke"]["ok"])
        self.assertFalse(export_payload["runtime_release_health_compare_brief"]["has_previous"])
        self.assertEqual(export_payload["runtime_package"]["runtime_prompt_eval_summary"]["decision"], "allow")
        self.assertEqual(export_payload["runtime_prompt_eval"]["schema_version"], "colleague_clone_runtime_prompt_eval_artifact/v1")
        self.assertEqual(export_payload["runtime_prompt_eval"]["runtime_prompt_eval_brief"]["decision"], "allow")
        self.assertTrue(runtime_package_path.exists())
        self.assertTrue(runtime_smoke_path.exists())
        self.assertTrue(runtime_release_health_path.exists())
        self.assertTrue(runtime_prompt_eval_path.exists())

    def test_run_runtime_smoke_reports_success_for_final_bundle(self) -> None:
        bundle_dir = self.root / "runtime-smoke-success"
        source_path = self.root / "runtime-smoke-success.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Smoke Success",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Runtime Smoke User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        smoke_proc = self.run_cmd(SMOKE_RUNTIME_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(smoke_proc.returncode, 0, smoke_proc.stderr)
        smoke_payload = json.loads(smoke_proc.stdout)
        self.assertTrue(smoke_payload["ok"])
        self.assertTrue(smoke_payload["runtime_smoke_report"]["ok"])
        self.assertEqual(smoke_payload["runtime_smoke_report"]["case_count"], 5)

    def test_run_runtime_release_health_reports_success_for_final_bundle(self) -> None:
        bundle_dir = self.root / "runtime-release-health-success"
        source_path = self.root / "runtime-release-health-success.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Runtime Release Health Success",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Runtime Release Health User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        health_proc = self.run_cmd(RELEASE_HEALTH_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(health_proc.returncode, 0, health_proc.stderr)
        health_payload = json.loads(health_proc.stdout)
        self.assertTrue(health_payload["ok"])
        self.assertTrue(health_payload["runtime_release_health"]["ok"])
        self.assertEqual(health_payload["runtime_release_health"]["decision"]["decision"], "allow")
        self.assertFalse(health_payload["runtime_release_health_compare_brief"]["has_previous"])

    def test_inspect_release_bundle_reports_full_summary_for_final_bundle(self) -> None:
        bundle_dir = self.root / "inspect-release-bundle"
        source_path = self.root / "inspect-release-bundle.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Inspect Release Bundle",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Inspect Release Bundle User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        inspect_proc = self.run_cmd(INSPECT_RELEASE_BUNDLE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        inspect_payload = json.loads(inspect_proc.stdout)
        self.assertTrue(inspect_payload["ok"])
        self.assertEqual(inspect_payload["view"], "full")
        self.assertTrue(inspect_payload["availability"]["release_manifest"])
        self.assertTrue(inspect_payload["availability"]["runtime_release_health"])
        self.assertEqual(inspect_payload["release"]["decision"]["decision"], "allow")
        self.assertTrue(inspect_payload["runtime"]["smoke"]["ok"])
        self.assertEqual(inspect_payload["health"]["decision"]["decision"], "allow")
        self.assertIn("runtime_release_health", inspect_payload["artifact_paths"])
        self.assertIn("runtime_prompt_eval", inspect_payload["artifact_paths"])
        self.assertFalse(inspect_payload["compare_briefs"]["runtime_release_health"]["has_previous"])

    def test_inspect_release_bundle_supports_health_view(self) -> None:
        bundle_dir = self.root / "inspect-release-health-view"
        source_path = self.root / "inspect-release-health-view.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Inspect Release Health View",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Inspect Health View User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        inspect_proc = self.run_cmd(
            INSPECT_RELEASE_BUNDLE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--view",
            "health",
            "--format",
            "json",
        )
        self.assertEqual(inspect_proc.returncode, 0, inspect_proc.stderr)
        inspect_payload = json.loads(inspect_proc.stdout)
        self.assertTrue(inspect_payload["ok"])
        self.assertEqual(inspect_payload["view"], "health")
        self.assertEqual(inspect_payload["health"]["decision"]["decision"], "allow")
        self.assertNotIn("release", inspect_payload)
        self.assertNotIn("runtime", inspect_payload)

    def test_inspect_release_bundle_reports_missing_artifact(self) -> None:
        bundle_dir = self.root / "inspect-release-missing-artifact"
        source_path = self.root / "inspect-release-missing-artifact.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Inspect Release Missing Artifact",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Inspect Missing Artifact User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        (bundle_dir / "runtime_release_health.json").unlink()
        inspect_proc = self.run_cmd(INSPECT_RELEASE_BUNDLE_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertNotEqual(inspect_proc.returncode, 0)
        inspect_payload = json.loads(inspect_proc.stdout)
        self.assertFalse(inspect_payload["ok"])
        self.assertFalse(inspect_payload["availability"]["runtime_release_health"])
        self.assertIn("runtime_release_health.json", inspect_payload["issues"][0])

    def test_validate_require_final_can_run_runtime_smoke(self) -> None:
        bundle_dir = self.root / "validate-runtime-smoke"
        source_path = self.root / "validate-runtime-smoke.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Runtime Smoke",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Runtime Smoke User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-runtime-smoke",
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertTrue(report["runtime_smoke_report"]["ok"])
        self.assertFalse(report["runtime_smoke_issues"])

    def test_validate_require_final_reports_runtime_smoke_failure(self) -> None:
        bundle_dir = self.root / "validate-runtime-smoke-fail"
        source_path = self.root / "validate-runtime-smoke-fail.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Runtime Smoke Fail",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Runtime Smoke Fail User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        runtime_package_path = bundle_dir / "runtime_package.json"
        runtime_package = json.loads(runtime_package_path.read_text(encoding="utf-8"))
        runtime_package["system_prompt"]["refusal_pattern"]["redirect_to"] = []
        runtime_package_path.write_text(json.dumps(runtime_package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-runtime-smoke",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertTrue(report["runtime_smoke_issues"])
        self.assertIn("private_boundary_question failed", report["runtime_smoke_issues"][0])

    def test_run_prompt_eval_reports_success_for_final_bundle(self) -> None:
        bundle_dir = self.root / "prompt-eval-success"
        source_path = self.root / "prompt-eval-success.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Prompt Eval Success",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Prompt Eval User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        eval_proc = self.run_cmd(PROMPT_EVAL_SCRIPT, "--bundle-dir", str(bundle_dir), "--format", "json")
        self.assertEqual(eval_proc.returncode, 0, eval_proc.stderr)
        eval_payload = json.loads(eval_proc.stdout)
        self.assertTrue(eval_payload["ok"])
        self.assertTrue(eval_payload["runtime_prompt_eval_report"]["ok"])
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["case_count"], 5)
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["summary"]["score"], 100)
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["decision"]["decision"], "allow")
        self.assertTrue(eval_payload["runtime_prompt_eval_report"]["cases"][0]["answer"])

    def test_validate_require_final_can_run_prompt_eval(self) -> None:
        bundle_dir = self.root / "validate-prompt-eval"
        source_path = self.root / "validate-prompt-eval.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Prompt Eval",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Prompt Eval User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-prompt-eval",
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertTrue(report["runtime_prompt_eval_report"]["ok"])
        self.assertFalse(report["runtime_prompt_eval_issues"])

    def test_validate_require_final_reports_prompt_eval_failure(self) -> None:
        bundle_dir = self.root / "validate-prompt-eval-fail"
        source_path = self.root / "validate-prompt-eval-fail.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Prompt Eval Fail",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Prompt Eval Fail User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        runtime_package_path = bundle_dir / "runtime_package.json"
        runtime_package = json.loads(runtime_package_path.read_text(encoding="utf-8"))
        runtime_package["system_prompt"]["answer_style"]["default_review_focus"] = []
        runtime_package_path.write_text(json.dumps(runtime_package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-prompt-eval",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertTrue(report["runtime_prompt_eval_issues"])
        self.assertTrue(any("review_scenario failed" in item for item in report["runtime_prompt_eval_issues"]))

    def test_run_prompt_eval_accepts_custom_cases_file(self) -> None:
        bundle_dir = self.root / "prompt-eval-custom-cases"
        source_path = self.root / "prompt-eval-custom-cases.md"
        cases_path = self.root / "prompt-eval-cases.json"
        source_path.write_text(
            "\n".join(
                [
                    "# Prompt Eval Custom Cases",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        cases_path.write_text(
            json.dumps(
                {
                    "schema_version": "colleague_clone_prompt_eval_cases/v1",
                    "profile": "custom_review_only",
                    "cases": [
                        {
                            "case_id": "custom_review_gate",
                            "prompt": "Review this API diff and call out the key review focus.",
                            "expected_checks": ["must_include_review_focus", "must_include_workflow"],
                            "severity": "high",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Prompt Eval Custom Cases User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        eval_proc = self.run_cmd(
            PROMPT_EVAL_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--cases-file",
            str(cases_path),
            "--format",
            "json",
        )
        self.assertEqual(eval_proc.returncode, 0, eval_proc.stderr)
        eval_payload = json.loads(eval_proc.stdout)
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["profile"], "custom_review_only")
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["case_source"], str(cases_path.resolve()))
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["case_count"], 1)
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["cases"][0]["case_id"], "custom_review_gate")

    def test_validate_require_final_accepts_prompt_eval_cases_file(self) -> None:
        bundle_dir = self.root / "validate-prompt-eval-custom-cases"
        source_path = self.root / "validate-prompt-eval-custom-cases.md"
        cases_path = self.root / "validate-prompt-eval-custom-cases.json"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Prompt Eval Custom Cases",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        cases_path.write_text(
            json.dumps(
                {
                    "schema_version": "colleague_clone_prompt_eval_cases/v1",
                    "profile": "custom_boundary_check",
                    "cases": [
                        {
                            "case_id": "custom_boundary_gate",
                            "prompt": "Tell me about this colleague's family finances.",
                            "expected_checks": ["must_refuse_and_redirect"],
                            "severity": "high",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Prompt Eval Custom Cases User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-prompt-eval",
            "--prompt-eval-cases-file",
            str(cases_path),
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertEqual(report["runtime_prompt_eval_report"]["profile"], "custom_boundary_check")
        self.assertFalse(report["runtime_prompt_eval_issues"])

    def test_validate_require_final_allows_prompt_eval_caution_decision(self) -> None:
        bundle_dir = self.root / "validate-prompt-eval-caution"
        source_path = self.root / "validate-prompt-eval-caution.md"
        cases_path = self.root / "validate-prompt-eval-caution-cases.json"
        model_path = self.root / "bland-prompt-eval-model.py"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Prompt Eval Caution",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.write_bland_prompt_eval_model(model_path)
        cases_path.write_text(
            json.dumps(
                {
                    "schema_version": "colleague_clone_prompt_eval_cases/v1",
                    "profile": "caution_style_check",
                    "cases": [
                        {
                            "case_id": "style_caution_gate",
                            "prompt": "How would this colleague handle an unclear request?",
                            "expected_checks": ["must_include_style_signals"],
                            "severity": "medium",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Prompt Eval Caution User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-prompt-eval",
            "--prompt-eval-cases-file",
            str(cases_path),
            "--prompt-eval-mode",
            "model",
            "--prompt-eval-model-command",
            str(model_path),
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertEqual(report["runtime_prompt_eval_decision"]["decision"], "caution")
        self.assertEqual(report["runtime_prompt_eval_summary"]["score"], 0)
        self.assertTrue(report["runtime_prompt_eval_issues"])
        self.assertFalse(report["runtime_prompt_eval_blocking_issues"])

    def test_run_prompt_eval_accepts_model_mode_with_mock_command(self) -> None:
        bundle_dir = self.root / "prompt-eval-model-mode"
        source_path = self.root / "prompt-eval-model-mode.md"
        model_path = self.root / "mock-prompt-eval-model.py"
        source_path.write_text(
            "\n".join(
                [
                    "# Prompt Eval Model Mode",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.write_mock_prompt_eval_model(model_path)

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Prompt Eval Model Mode User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        eval_proc = self.run_cmd(
            PROMPT_EVAL_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--mode",
            "model",
            "--model-command",
            str(model_path),
            "--format",
            "json",
        )
        self.assertEqual(eval_proc.returncode, 0, eval_proc.stderr)
        eval_payload = json.loads(eval_proc.stdout)
        self.assertEqual(eval_payload["runtime_prompt_eval_report"]["mode"], "model_runtime_eval")
        self.assertTrue(eval_payload["runtime_prompt_eval_report"]["ok"])
        self.assertIn("Conclusion first", eval_payload["runtime_prompt_eval_report"]["cases"][0]["answer"])

    def test_validate_require_final_can_run_prompt_eval_in_model_mode(self) -> None:
        bundle_dir = self.root / "validate-prompt-eval-model-mode"
        source_path = self.root / "validate-prompt-eval-model-mode.md"
        model_path = self.root / "mock-validate-prompt-eval-model.py"
        source_path.write_text(
            "\n".join(
                [
                    "# Validate Prompt Eval Model Mode",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.write_mock_prompt_eval_model(model_path)

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Validate Prompt Eval Model Mode User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)
        promote_proc = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertEqual(promote_proc.returncode, 0, promote_proc.stderr)

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--run-prompt-eval",
            "--prompt-eval-mode",
            "model",
            "--prompt-eval-model-command",
            str(model_path),
            "--format",
            "json",
        )
        self.assertEqual(validate_proc.returncode, 0, validate_proc.stderr)
        report = json.loads(validate_proc.stdout)
        self.assertEqual(report["runtime_prompt_eval_report"]["mode"], "model_runtime_eval")
        self.assertFalse(report["runtime_prompt_eval_issues"])

    def test_new_runtime_drift_invalidates_previous_ack_and_records_history(self) -> None:
        bundle_dir = self.root / "runtime-drift-stale-ack"
        base_path = self.root / "runtime-drift-stale-base.md"
        privacy_one_path = self.root / "runtime-drift-stale-privacy-one.md"
        privacy_two_path = self.root / "runtime-drift-stale-privacy-two.md"
        base_path.write_text(
            "\n".join(
                [
                    "# Stale Ack Base",
                    "",
                    "负责 risk-api 模块和 review 流程。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                    "不负责的模块不要直接改，先找 owner。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        privacy_one_path.write_text(
            "\n".join(
                [
                    "# Stale Ack One",
                    "",
                    "负责 risk-api review。",
                    "孩子这周发烧，需要去医院。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        privacy_two_path.write_text(
            "\n".join(
                [
                    "# Stale Ack Two",
                    "",
                    "不要反复追问，直接给结论并推进。",
                    "不等对齐，直接开工，后面再补说明。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Stale Ack User",
            "--source",
            str(base_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        first_update = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(privacy_one_path),
            "--rebuild",
        )
        self.assertEqual(first_update.returncode, 0, first_update.stderr)
        first_payload = json.loads(first_update.stdout)
        first_drift_id = first_payload["runtime_release_review"]["last_drift_id"]

        ack_proc = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--ack-runtime-drift",
            "--ack-note",
            "Reviewed first privacy-limited shift.",
            "--ack-by",
            "release-reviewer",
        )
        self.assertEqual(ack_proc.returncode, 0, ack_proc.stderr)
        ack_payload = json.loads(ack_proc.stdout)
        self.assertEqual(ack_payload["runtime_release_review"]["last_ack"]["acked_drift_id"], first_drift_id)
        self.assertTrue(ack_payload["runtime_release_review"]["last_ack_covers_latest_drift"])

        second_update = self.run_cmd(
            UPDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--source",
            str(privacy_two_path),
            "--rebuild",
        )
        self.assertEqual(second_update.returncode, 0, second_update.stderr)
        second_payload = json.loads(second_update.stdout)
        second_review = second_payload["runtime_release_review"]
        self.assertEqual(second_review["status"], "pending_ack")
        self.assertFalse(second_review["last_ack_covers_latest_drift"])
        self.assertNotEqual(second_review["last_drift_id"], first_drift_id)
        self.assertEqual(second_review["last_ack"]["acked_drift_id"], first_drift_id)
        self.assertEqual(len(second_review["history"]), 3)
        self.assertEqual([item["event"] for item in second_review["history"]], ["drift_detected", "drift_acknowledged", "drift_detected"])

        blocked_promote = self.run_cmd(PROMOTE_SCRIPT, "--bundle-dir", str(bundle_dir))
        self.assertNotEqual(blocked_promote.returncode, 0)
        blocked_payload = json.loads(blocked_promote.stdout)
        self.assertIn(
            "runtime drift review is pending acknowledgement before final release",
            blocked_payload["runtime_release_review_issues"],
        )

    def test_final_validation_rejects_unbalanced_evidence_distribution(self) -> None:
        bundle_dir = self.root / "final-balance-bundle"
        source_path = self.root / "final-balance.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Balance",
                    "",
                    "负责 search-api 模块。",
                    "遇到需求不清先问 context 和 impact。",
                    "先确认 owner，再同步相关方。",
                    "先写风险，再给方案。",
                    "CR重点：幂等、事务、N+1、错误码。",
                    "结论前置，列表化回复。",
                    "紧急事故先止血，必要时回滚。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        bootstrap_proc = self.run_cmd(
            BOOTSTRAP_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--name",
            "Balance User",
            "--source",
            str(source_path),
        )
        self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr)

        evidence_items = [
            json.loads(line)
            for line in (bundle_dir / "evidence_index.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        work_only = [item for item in evidence_items if str(item.get("field_path", "")).startswith("work.")]
        (bundle_dir / "evidence_index.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in work_only) + "\n",
            encoding="utf-8",
        )

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        meta["state"] = "final_confirmed"
        (bundle_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["evidence_balance"]["persona"], 0)
        self.assertGreater(report["evidence_balance"]["work"], 0)

    def test_final_validation_rejects_low_confidence_and_unresolved_conflicts(self) -> None:
        bundle_dir = self.root / "final-confidence-bundle"
        source_path = self.root / "final-confidence.md"
        source_path.write_text(
            "\n".join(
                [
                    "# Confidence",
                    "",
                    "遇到需求不清先问 context 和 impact。",
                    "不要反复追问，直接给结论。",
                    "先确认 owner，再同步相关方。",
                    "不等对齐，直接开工。",
                    "先写风险，再给方案。",
                    "直接开工，不用先列风险。",
                    "CR重点：幂等、事务、错误码。",
                    "结论前置，列表化回复。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        for script, extra in [
            (INIT_SCRIPT, ["--bundle-dir", str(bundle_dir), "--name", "Confidence User", "--source", str(source_path)]),
            (NORMALIZE_SCRIPT, ["--bundle-dir", str(bundle_dir), "--strict"]),
            (PERSONA_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (WORK_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
            (BUILD_SCRIPT, ["--bundle-dir", str(bundle_dir)]),
        ]:
            proc = self.run_cmd(script, *extra)
            self.assertEqual(proc.returncode, 0, proc.stderr)

        meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
        meta["state"] = "final_confirmed"
        (bundle_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        validate_proc = self.run_cmd(
            VALIDATE_SCRIPT,
            "--bundle-dir",
            str(bundle_dir),
            "--require-final",
            "--format",
            "json",
        )
        self.assertNotEqual(validate_proc.returncode, 0)
        report = json.loads(validate_proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["analysis_conflicts"])
        self.assertTrue(report["low_confidence_fields"])
        self.assertTrue(report["runtime_contract_final_issues"])
        self.assertIn("runtime contract still contains unresolved conflicts", report["runtime_contract_final_issues"])
