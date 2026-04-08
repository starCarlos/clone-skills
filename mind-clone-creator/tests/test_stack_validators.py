from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import extract_workflow_draft


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(stdout: str) -> dict:
    return json.loads(stdout)


def replace_in_marked_block(text: str, start: str, end: str, old: str, new: str, count: int = 1) -> str:
    try:
        prefix, remainder = text.split(start, 1)
        block, suffix = remainder.split(end, 1)
    except ValueError as exc:
        raise AssertionError(f"missing marker block: {start} .. {end}") from exc
    updated_block = block.replace(old, new, count)
    if updated_block == block:
        raise AssertionError(f"pattern not found inside marker block: {old}")
    return prefix + start + updated_block + end + suffix


class StackValidatorFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="mind-clone-validator-")
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def run_cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def copy_repo_docs_fixture(self) -> Path:
        fixture_root = Path(tempfile.mkdtemp(prefix="repo-docs-fixture-", dir=self.root))
        shutil.copytree(REPO_ROOT / "scripts", fixture_root / "scripts")
        shutil.copytree(REPO_ROOT / "references", fixture_root / "references")
        shutil.copytree(REPO_ROOT / "examples", fixture_root / "examples")
        for name in ["README.md", "RELEASE_READINESS_CHECKLIST.md"]:
            shutil.copy2(REPO_ROOT / name, fixture_root / name)
        return fixture_root

    def test_personal_skill_validator_reports_source_artifact_mismatch(self) -> None:
        skill_dir = self.root / "personal-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("skill\n", encoding="utf-8")
        (skill_dir / "clone_config.yaml").write_text("output-clone\n", encoding="utf-8")
        (skill_dir / "mind_profile.md").write_text("mind\n", encoding="utf-8")
        (skill_dir / "system_prompt.md").write_text("prompt\n", encoding="utf-8")
        (skill_dir / "eval_report.md").write_text("eval\n", encoding="utf-8")
        (skill_dir / "research_digest.md").write_text("research\n", encoding="utf-8")
        (skill_dir / "workflow_blueprint.md").write_text("workflow\n", encoding="utf-8")
        readme = skill_dir / "README.md"
        readme.write_text("- clone_name: Foo\n- profession: AI Engineer\n- draft_status: final\n", encoding="utf-8")

        upstream_clone = self.root / "upstream-clone.yaml"
        upstream_clone.write_text("different-clone\n", encoding="utf-8")
        write_json(
            skill_dir / "personal_clone_skill_manifest.json",
            {
                "type": "personal_clone_skill",
                "clone_name": "Foo",
                "profession": "AI Engineer",
                "draft_status": "final",
                "quality_score": 80,
                "source_artifacts": {
                    "clone_config": {"path": str(upstream_clone), "exists": True, "kind": "file"},
                    "mind_profile": {"path": str(skill_dir / "mind_profile.md"), "exists": True, "kind": "file"},
                    "system_prompt": {"path": str(skill_dir / "system_prompt.md"), "exists": True, "kind": "file"},
                    "eval_report": {"path": str(skill_dir / "eval_report.md"), "exists": True, "kind": "file"},
                    "research_digest": {"path": str(skill_dir / "research_digest.md"), "exists": True, "kind": "file"},
                    "workflow_blueprint": {"path": str(skill_dir / "workflow_blueprint.md"), "exists": True, "kind": "file"},
                },
                "files": {
                    "skill_md": str(skill_dir / "SKILL.md"),
                    "clone_config": str(skill_dir / "clone_config.yaml"),
                    "mind_profile": str(skill_dir / "mind_profile.md"),
                    "system_prompt": str(skill_dir / "system_prompt.md"),
                    "eval_report": str(skill_dir / "eval_report.md"),
                    "research_digest": str(skill_dir / "research_digest.md"),
                    "workflow_blueprint": str(skill_dir / "workflow_blueprint.md"),
                },
            },
        )
        proc = self.run_cmd(
            "scripts/validate_personal_clone_skill.py",
            "--manifest",
            str(skill_dir / "personal_clone_skill_manifest.json"),
            "--readme",
            str(readme),
            "--format",
            "json",
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["source_artifacts"]["mismatched_files"])

    def test_workflow_skill_validator_reports_missing_readme(self) -> None:
        skill_dir = self.root / "workflow-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "clone_config.yaml").write_text("clone\n", encoding="utf-8")
        (skill_dir / "workflow_blueprint.md").write_text("blueprint\n", encoding="utf-8")
        write_json(
            skill_dir / "workflow_clone_skill_manifest.json",
            {
                "type": "workflow_clone_skill",
                "clone_name": "Foo",
                "profession": "AI Engineer",
                "workflow_name": "Bar",
                "draft_status": "final",
                "quality_score": 80,
                "files": {
                    "skill_md": str(skill_dir / "SKILL.md"),
                    "clone_config": str(skill_dir / "clone_config.yaml"),
                    "workflow_blueprint": str(skill_dir / "workflow_blueprint.md"),
                },
            },
        )
        proc = self.run_cmd(
            "scripts/validate_workflow_clone_skill.py",
            "--manifest",
            str(skill_dir / "workflow_clone_skill_manifest.json"),
            "--readme",
            str(skill_dir / "README.md"),
            "--format",
            "json",
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["readme_exists"])

    def test_extract_workflow_draft_ignores_blank_stage_confirmation_placeholders(self) -> None:
        interview = self.root / "workflow_interview.md"
        interview.write_text(
            "\n".join(
                [
                    "# workflow interview",
                    "### W1. 这类工作从什么触发？",
                    "- 收到新需求",
                    "### W2. 完成的标准是什么？",
                    "- 产出可交付首版",
                    "### W3. 中间大概经过几个阶段？",
                    "1. 接收需求",
                    "2. 澄清验收标准",
                    "3. 交付与复盘",
                    "### W4. 每个阶段你主要用什么工具？",
                    "- 需求文档",
                    "- 代码仓库",
                    "- 交付文档",
                    "### W5. 哪些环节最容易卡住？",
                    "- 需求模糊",
                    "### W6. 哪些决策必须你本人来做？",
                    "- 需求优先级取舍",
                    "### W7. 最终交给对方的是什么？",
                    "- 代码",
                    "- 风险说明",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        stage_confirmation = self.root / "stage_confirmation.md"
        stage_confirmation.write_text(
            "\n".join(
                [
                    "# stage confirmation",
                    "### 缺失阶段",
                    "- ",
                    "### 顺序修正",
                    "- ",
                    "### 迭代或回环关系",
                    "- ",
                    "### 必须人工拍板的节点",
                    "- ",
                    "### 你确认后的最终阶段",
                    "1. ",
                    "2. ",
                    "3. ",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        payload = extract_workflow_draft.parse_interview(
            interview,
            "测试工作流",
            "完成一个首版需求",
            stage_confirmation,
        )
        self.assertEqual(payload["confirmed_stages"], ["接收需求", "澄清验收标准", "交付与复盘"])
        self.assertEqual(payload["stage_confirmation_notes"]["missing_stages"], [])
        self.assertEqual(payload["stages"][0]["name"], "接收需求")
        self.assertNotEqual(payload["stages"][0]["goal"], "")
        self.assertTrue(payload["stage_actions"])
        self.assertTrue(payload["tool_map"])
        self.assertTrue(payload["transition_rules"])
        self.assertTrue(payload["human_checkpoints"])

    def test_workflow_skill_validator_reports_placeholder_blueprint(self) -> None:
        skill_dir = self.root / "workflow-skill-placeholder"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("skill\n", encoding="utf-8")
        (skill_dir / "clone_config.yaml").write_text("clone\n", encoding="utf-8")
        (skill_dir / "workflow_blueprint.md").write_text(
            "\n".join(
                [
                    "# 占位蓝图",
                    "## 阶段蓝图",
                    "### 1. 阶段1",
                    "",
                    "- 目标：暂无",
                    "- 输入：暂无",
                    "- 输出：暂无",
                    "- 完成判断：暂无",
                    "",
                    "## 阶段动作",
                    "暂无阶段动作",
                    "",
                    "## 工具映射",
                    "暂无工具映射",
                    "",
                    "## 阶段切换规则",
                    "暂无阶段切换规则",
                    "",
                    "## 人工介入点",
                    "### 未命名阶段",
                    "",
                    "- 触发条件：暂无",
                    "- 需要人工介入的原因：暂无",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (skill_dir / "mind_profile.md").write_text("mind\n", encoding="utf-8")
        (skill_dir / "system_prompt.md").write_text("prompt\n", encoding="utf-8")
        (skill_dir / "workflow_task_state.yaml").write_text("state: draft\n", encoding="utf-8")
        readme = skill_dir / "README.md"
        readme.write_text(
            "- clone_name: Foo\n- profession: AI Engineer\n- workflow_name: Bar\n- draft_status: final\n",
            encoding="utf-8",
        )
        write_json(
            skill_dir / "workflow_clone_skill_manifest.json",
            {
                "type": "workflow_clone_skill",
                "clone_name": "Foo",
                "profession": "AI Engineer",
                "workflow_name": "Bar",
                "draft_status": "final",
                "quality_score": 80,
                "source_artifacts": {
                    "clone_config": {"path": str(skill_dir / "clone_config.yaml"), "exists": True, "kind": "file"},
                    "workflow_blueprint": {"path": str(skill_dir / "workflow_blueprint.md"), "exists": True, "kind": "file"},
                    "mind_profile": {"path": str(skill_dir / "mind_profile.md"), "exists": True, "kind": "file"},
                    "system_prompt": {"path": str(skill_dir / "system_prompt.md"), "exists": True, "kind": "file"},
                    "workflow_task_state": {"path": str(skill_dir / "workflow_task_state.yaml"), "exists": True, "kind": "file"},
                },
                "files": {
                    "skill_md": str(skill_dir / "SKILL.md"),
                    "clone_config": str(skill_dir / "clone_config.yaml"),
                    "workflow_blueprint": str(skill_dir / "workflow_blueprint.md"),
                    "mind_profile": str(skill_dir / "mind_profile.md"),
                    "system_prompt": str(skill_dir / "system_prompt.md"),
                    "workflow_task_state": str(skill_dir / "workflow_task_state.yaml"),
                },
            },
        )

        proc = self.run_cmd(
            "scripts/validate_workflow_clone_skill.py",
            "--manifest",
            str(skill_dir / "workflow_clone_skill_manifest.json"),
            "--readme",
            str(readme),
            "--format",
            "json",
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertFalse(report["blueprint_quality"]["ok"])
        self.assertTrue(report["blueprint_quality"]["generic_stage_titles"])

        blueprint_proc = self.run_cmd(
            "scripts/validate_workflow_blueprint.py",
            "--input",
            str(skill_dir / "workflow_blueprint.md"),
            "--format",
            "json",
        )
        self.assertNotEqual(blueprint_proc.returncode, 0)
        blueprint_report = read_json(blueprint_proc.stdout)
        self.assertFalse(blueprint_report["ok"])
        self.assertTrue(blueprint_report["placeholder_sections"])

    def test_validate_clone_stack_reports_source_artifact_contract_failure(self) -> None:
        root = self.root / "stack"
        bundle_dir = root / "bundle"
        pipeline_dir = root / "pipeline"
        runtime_dir = root / "runtime"
        blueprint = root / "workflow_blueprint.md"
        clone_config = root / "clone_config.yaml"
        root.mkdir(parents=True, exist_ok=True)
        blueprint.write_text("blueprint\n", encoding="utf-8")
        clone_config.write_text("clone\n", encoding="utf-8")

        bundle_manifest = bundle_dir / "working_clone_bundle_manifest.json"
        bundle_summary = bundle_dir / "working_clone_until_final_summary.json"
        bundle_readme = bundle_dir / "WORKING_CLONE_BUNDLE_README.md"
        pipeline_manifest = pipeline_dir / "workflow_blueprint_pipeline_manifest.json"
        pipeline_readme = pipeline_dir / "WORKFLOW_BLUEPRINT_PIPELINE_README.md"
        runtime_manifest = runtime_dir / "workflow_runtime_manifest.json"
        runtime_readme = runtime_dir / "WORKFLOW_RUNTIME_README.md"
        for path in [bundle_manifest, bundle_summary, bundle_readme, pipeline_manifest, pipeline_readme, runtime_manifest, runtime_readme]:
            path.parent.mkdir(parents=True, exist_ok=True)

        command = "python3 scripts/run_workflow_turn.py --workflow-blueprint /tmp/workflow_blueprint.md --state /tmp/state.yaml --input <your-update> --workspace . --artifact-dir workflow-runtime-artifacts --profession AI Engineer --output-dir /tmp/out --execute-safe"
        bundle_readme.write_text(f"## Recommended Next Command\n```bash\n{command}\n```\n", encoding="utf-8")
        pipeline_readme.write_text(f"## Recommended Next Command\n```bash\n{command}\n```\n", encoding="utf-8")
        runtime_readme.write_text(f"## Recommended Next Command\n```bash\n{command}\n```\n", encoding="utf-8")

        write_json(
            bundle_manifest,
            {
                "workflow_blueprint": str(blueprint),
                "command_style": "repo_relative_scripts",
                "steps": {"personal_clone_skill": True, "workflow_pipeline": True, "workflow_runtime_bundle": True},
                "pending_interview_action_group_counts": {
                    "current_executable_now_count": 0,
                    "requires_manual_edit_first_count": 0,
                    "needs_content_edit_count": 0,
                    "needs_human_confirmation_count": 0,
                    "needs_build_step_count": 0,
                },
                "recommended_next_command": {
                    "mode": "ready_to_run",
                    "label": "run_workflow_turn",
                    "command": command,
                    "scope": "workflow",
                    "section": "runtime_turn",
                    "manual_edit_required": "false",
                    "priority": "low",
                },
                "source_artifacts": {
                    "personal_interview": {"path": str(root / "missing-personal-interview.md"), "exists": False, "kind": "missing"}
                },
            },
        )
        write_json(
            bundle_summary,
            {
                "recommended_next_command": {
                    "mode": "ready_to_run",
                    "label": "run_workflow_turn",
                    "command": command,
                    "scope": "workflow",
                    "section": "runtime_turn",
                    "manual_edit_required": "false",
                    "priority": "low",
                },
                "pending_interview_action_groups": {
                    "current_executable_now": [],
                    "requires_manual_edit_first": [],
                    "needs_content_edit": [],
                    "needs_human_confirmation": [],
                    "needs_build_step": [],
                },
            },
        )
        write_json(
            pipeline_manifest,
            {
                "clone_config": str(clone_config),
                "blueprint": str(blueprint),
                "command_style": "repo_relative_scripts",
                "steps": {"stage_confirmation": False, "blueprint": True, "workflow_clone_skill": False, "workflow_runtime_bundle": False},
                "recommended_next_command": {
                    "mode": "ready_to_run",
                    "label": "run_workflow_turn",
                    "command": command,
                    "scope": "workflow",
                    "section": "runtime_turn",
                    "manual_edit_required": "false",
                    "priority": "low",
                },
                "source_artifacts": {},
            },
        )
        write_json(
            runtime_manifest,
            {
                "clone_config": str(clone_config),
                "workflow_blueprint": str(blueprint),
                "state_path": str(root / "state.yaml"),
                "command_style": "repo_relative_scripts",
                "recommended_next_command": {
                    "mode": "ready_to_run",
                    "label": "run_workflow_turn",
                    "command": command,
                    "scope": "workflow_runtime",
                    "section": "single_turn",
                    "manual_edit_required": "false",
                    "priority": "medium",
                },
                "source_artifacts": {},
            },
        )

        proc = self.run_cmd(
            "scripts/validate_clone_stack.py",
            "--bundle-manifest",
            str(bundle_manifest),
            "--bundle-summary",
            str(bundle_summary),
            "--bundle-readme",
            str(bundle_readme),
            "--pipeline-manifest",
            str(pipeline_manifest),
            "--pipeline-readme",
            str(pipeline_readme),
            "--runtime-manifest",
            str(runtime_manifest),
            "--runtime-readme",
            str(runtime_readme),
            "--format",
            "json",
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["checks"]["source_artifact_contracts"]["ok"])

    def test_validate_working_clone_bundle_requires_workflow_clone_skill_when_workflow_enabled(self) -> None:
        bundle_dir = self.root / "bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        interview_state = bundle_dir / "clone_interview_state.json"
        write_json(
            interview_state,
            {
                "personal_progress": {"section_statuses": []},
                "workflow_progress": {"section_statuses": []},
            },
        )
        manifest = bundle_dir / "working_clone_bundle_manifest.json"
        write_json(
            manifest,
            {
                "interview_state": str(interview_state),
                "interview_validation": {
                    "personal_final_ready": True,
                    "workflow_final_ready": True,
                },
                "steps": {
                    "workflow_enabled": True,
                    "personal_clone_skill": True,
                    "workflow_pipeline": True,
                    "workflow_clone_skill": False,
                    "workflow_runtime_bundle": True,
                },
            },
        )

        proc = self.run_cmd(
            "scripts/validate_working_clone_bundle.py",
            "--manifest",
            str(manifest),
            "--format",
            "json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = read_json(proc.stdout)
        self.assertFalse(report["final_ready"])
        self.assertFalse(report["workflow_clone_skill_ready"])
        self.assertTrue(any(item["item"] == "workflow_clone_skill" for item in report["blockers"]))

    def test_validate_working_clone_bundle_keeps_workflow_track_open_before_target_is_defined(self) -> None:
        bundle_dir = self.root / "bundle-pending-target"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        interview_state = bundle_dir / "clone_interview_state.json"
        write_json(
            interview_state,
            {
                "personal_progress": {"section_statuses": []},
                "workflow_progress": {"section_statuses": []},
            },
        )
        manifest = bundle_dir / "working_clone_bundle_manifest.json"
        write_json(
            manifest,
            {
                "interview_state": str(interview_state),
                "work_unit": "待确认的第一类典型工作",
                "interview_validation": {
                    "personal_final_ready": True,
                    "workflow_final_ready": False,
                },
                "steps": {
                    "workflow_enabled": True,
                    "workflow_target_defined": False,
                    "personal_clone_skill": True,
                    "workflow_pipeline": False,
                    "workflow_clone_skill": False,
                    "workflow_runtime_bundle": False,
                },
            },
        )

        proc = self.run_cmd(
            "scripts/validate_working_clone_bundle.py",
            "--manifest",
            str(manifest),
            "--format",
            "json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = read_json(proc.stdout)
        blocker_items = {item["item"] for item in report["blockers"]}

        self.assertFalse(report["final_ready"])
        self.assertFalse(report["workflow_target_defined"])
        self.assertIn("workflow_target", blocker_items)
        self.assertNotIn("workflow_pipeline", blocker_items)
        self.assertNotIn("workflow_clone_skill", blocker_items)
        self.assertNotIn("workflow_runtime_bundle", blocker_items)

    def test_validate_repo_docs_succeeds_on_current_repo(self) -> None:
        proc = self.run_cmd("scripts/validate_repo_docs.py", "--format", "json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = read_json(proc.stdout)
        self.assertTrue(report["ok"])
        self.assertFalse(report["missing_docs"])
        self.assertFalse(report["capability_index_render_mismatch"])
        self.assertFalse(report["release_checklist_missing_patterns"])
        self.assertFalse(report["release_checklist_render_mismatch"])
        self.assertFalse(report["current_flow_render_mismatch"])
        self.assertFalse(report["readme_operator_render_mismatch"])
        self.assertFalse(report["operator_playbook_render_mismatch"])
        self.assertFalse(report["new_maintainer_operator_render_mismatch"])
        self.assertFalse(report["doc_router_render_mismatch"])
        self.assertFalse(report["failure_guide_render_mismatch"])
        self.assertFalse(report["missing_script_refs"])

    def test_render_operator_command_docs_check_succeeds_on_current_repo(self) -> None:
        proc = self.run_cmd("scripts/render_operator_command_docs.py", "--check")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_render_operator_command_docs_reports_unknown_doc_ref(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        source = fixture_root / "references" / "operator_commands.json"
        source.write_text(
            source.read_text(encoding="utf-8").replace('"doc_ref": "current_flow"', '"doc_ref": "missing_doc_ref"', 1),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown doc_ref", proc.stderr)

    def test_render_operator_command_docs_reports_unknown_inspect_ref(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        source = fixture_root / "references" / "operator_commands.json"
        source.write_text(
            source.read_text(encoding="utf-8").replace('"inspect_ref": "workflow_interview"', '"inspect_ref": "missing_inspect_ref"', 1),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown inspect_ref", proc.stderr)

    def test_validate_repo_docs_reports_missing_readme_operator_command(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        readme = fixture_root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace("diff stack", "stack compare missing"),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("diff stack", report["readme_missing_patterns"])

    def test_validate_repo_docs_reports_release_checklist_missing_pattern(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        checklist = fixture_root / "RELEASE_READINESS_CHECKLIST.md"
        checklist.write_text(
            checklist.read_text(encoding="utf-8").replace(
                "<!-- BEGIN GENERATED: release-checklist-validation-commands -->",
                "<!-- BEGIN GENERATED: release-checklist-validation-missing -->",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn(
            "<!-- BEGIN GENERATED: release-checklist-validation-commands -->",
            report["release_checklist_missing_patterns"],
        )

    def test_validate_repo_docs_reports_release_checklist_handoff_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        checklist = fixture_root / "RELEASE_READINESS_CHECKLIST.md"
        checklist.write_text(
            replace_in_marked_block(
                checklist.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: release-checklist-handoff-items -->",
                "<!-- END GENERATED: release-checklist-handoff-items -->",
                "- [ ] 原始 explain 里的 `candidate_rejections` 现在也会压成单行非零摘要；如果所有类别都是 `0`，该段会直接省略",
                "- [ ] release checklist handoff drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["release_checklist_render_mismatch"])

    def test_render_operator_command_docs_check_reports_capability_index_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        capability_index = fixture_root / "references" / "capability_index.md"
        capability_index.write_text(
            capability_index.read_text(encoding="utf-8").replace(
                "- `scripts/stack_discovery.py`",
                "- `scripts/stack-discovery-missing.py`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/capability_index.md", proc.stderr)

    def test_validate_repo_docs_reports_missing_new_maintainer_pattern(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        new_maintainer = fixture_root / "references" / "new_maintainer_first_15_minutes.md"
        new_maintainer.write_text(
            new_maintainer.read_text(encoding="utf-8").replace("validate_repo_docs.py --format json", "validate repo docs missing"),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("validate_repo_docs.py --format json", report["new_maintainer_missing_patterns"])

    def test_validate_repo_docs_reports_release_order_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        new_maintainer = fixture_root / "references" / "new_maintainer_first_15_minutes.md"
        text = new_maintainer.read_text(encoding="utf-8")
        text = text.replace(
            "- 先跑文档防漂移校验：\n  `python3 scripts/validate_repo_docs.py --format json`\n- 再重建一份 sample stack：\n  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`",
            "- 先重建一份 sample stack：\n  `python3 scripts/rebuild_sample_stack.py --output-root /tmp/mind-clone-sample-stack`\n- 再跑文档防漂移校验：\n  `python3 scripts/validate_repo_docs.py --format json`",
        )
        new_maintainer.write_text(text, encoding="utf-8")

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["release_readiness_order_issues"])
        self.assertIn("new_maintainer operator path", report["release_readiness_order_issues"][0])

    def test_validate_repo_docs_reports_missing_operator_command_contract_pattern(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        contract = fixture_root / "references" / "operator_command_contract.md"
        contract.write_text(
            contract.read_text(encoding="utf-8").replace("doctor current-stack", "doctor current stack missing"),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("doctor current-stack", report["operator_command_contract_missing_patterns"])

    def test_validate_repo_docs_reports_operator_command_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        summary = fixture_root / "references" / "operator_command_summary.md"
        summary.write_text(summary.read_text(encoding="utf-8").rstrip() + "\n<!-- manual drift -->\n", encoding="utf-8")

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["operator_command_summary_render_mismatch"])

    def test_render_operator_command_docs_check_reports_readme_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        readme = fixture_root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "- `doctor latest-stack`",
                "- `doctor latest stack missing`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("README.md", proc.stderr)

    def test_validate_repo_docs_reports_readme_operator_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        readme = fixture_root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "- `doctor latest-stack`",
                "- `doctor latest stack missing`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["readme_operator_render_mismatch"])

    def test_render_operator_command_docs_check_reports_doc_router_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        doc_router = fixture_root / "references" / "doc_router.md"
        doc_router.write_text(
            doc_router.read_text(encoding="utf-8").replace(
                "operator_command_summary.md",
                "operator_command_summary_missing.md",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/doc_router.md", proc.stderr)

    def test_validate_repo_docs_reports_doc_router_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        doc_router = fixture_root / "references" / "doc_router.md"
        doc_router.write_text(
            doc_router.read_text(encoding="utf-8").replace(
                "operator_command_summary.md",
                "operator_command_summary_missing.md",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["doc_router_render_mismatch"])

    def test_render_operator_command_docs_check_reports_doc_router_path_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        doc_router = fixture_root / "references" / "doc_router.md"
        doc_router.write_text(
            doc_router.read_text(encoding="utf-8").replace(
                "1. [README.md]",
                "1. [README-missing.md]",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/doc_router.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_failure_guide_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            failure_guide.read_text(encoding="utf-8").replace(
                "doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json",
                "doctor latest stack missing",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_validate_repo_docs_reports_failure_guide_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            failure_guide.read_text(encoding="utf-8").replace(
                "doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json",
                "doctor latest stack missing",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_validate_repo_docs_reports_failure_guide_release_inspect_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-release-inspect -->",
                "<!-- END GENERATED: failure-guide-release-inspect -->",
                "- `release-logs/`",
                "- release inspect prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_validate_repo_docs_reports_failure_guide_new_inspect_render_mismatches(self) -> None:
        cases = [
            (
                "<!-- BEGIN GENERATED: failure-guide-personal-empty-inspect -->",
                "<!-- END GENERATED: failure-guide-personal-empty-inspect -->",
                "- `working_clone_bundle_manifest.json`",
                "- personal empty inspect prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-next-interview-inspect -->",
                "<!-- END GENERATED: failure-guide-next-interview-inspect -->",
                "- `clone_interview_state.json`",
                "- next interview inspect prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-eval-draft-inspect -->",
                "<!-- END GENERATED: failure-guide-eval-draft-inspect -->",
                "- `clone_config.yaml`",
                "- eval draft inspect prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-inspect -->",
                "<!-- END GENERATED: failure-guide-workflow-blocker-inspect -->",
                "- working bundle / pipeline README 里的 `recommended_next_command`",
                "- workflow blocker inspect prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-inspect -->",
                "<!-- END GENERATED: failure-guide-stage-confirmation-inspect -->",
                "- `workflow_interview.md`",
                "- stage confirmation inspect prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-runtime-inspect -->",
                "<!-- END GENERATED: failure-guide-runtime-inspect -->",
                "- 本轮 turn 输出目录",
                "- runtime inspect prose drift injected",
            ),
        ]

        for start_marker, end_marker, original, replacement in cases:
            with self.subTest(start_marker=start_marker):
                fixture_root = self.copy_repo_docs_fixture()
                failure_guide = fixture_root / "references" / "failure_path_guide.md"
                failure_guide.write_text(
                    replace_in_marked_block(
                        failure_guide.read_text(encoding="utf-8"),
                        start_marker,
                        end_marker,
                        original,
                        replacement,
                    ),
                    encoding="utf-8",
                )

                proc = subprocess.run(
                    [
                        "python3",
                        str(fixture_root / "scripts" / "validate_repo_docs.py"),
                        "--repo-root",
                        str(fixture_root),
                        "--format",
                        "json",
                    ],
                    cwd=fixture_root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(proc.returncode, 0)
                report = read_json(proc.stdout)
                self.assertFalse(report["ok"])
                self.assertTrue(report["failure_guide_render_mismatch"])

    def test_validate_repo_docs_reports_failure_guide_workflow_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            failure_guide.read_text(encoding="utf-8").replace(
                "refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json",
                "refresh_workflow_blueprint_pipeline.py --manifest /tmp/pipeline-missing.json",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_validate_repo_docs_reports_failure_guide_personal_empty_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-personal-empty-commands -->",
                "<!-- END GENERATED: failure-guide-personal-empty-commands -->",
                "`python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
                "`python3 scripts/refresh_working_clone_bundle_missing.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_render_operator_command_docs_check_reports_failure_guide_stage_confirmation_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-commands -->",
                "<!-- END GENERATED: failure-guide-stage-confirmation-commands -->",
                "`python3 scripts/refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json`",
                "`python3 scripts/refresh_workflow_pipeline_missing.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_validate_repo_docs_reports_failure_guide_next_interview_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-next-interview-commands -->",
                "<!-- END GENERATED: failure-guide-next-interview-commands -->",
                "`python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
                "`python3 scripts/refresh_working_clone_bundle_next_missing.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_validate_repo_docs_reports_failure_guide_workflow_blocker_steps_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-next-steps -->",
                "<!-- END GENERATED: failure-guide-workflow-blocker-next-steps -->",
                "- 再补 W1-W7",
                "- workflow blocker prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_render_operator_command_docs_check_reports_failure_guide_eval_draft_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-eval-draft-commands -->",
                "<!-- END GENERATED: failure-guide-eval-draft-commands -->",
                "`python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
                "`python3 scripts/refresh_working_clone_bundle_eval_missing.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_failure_guide_stage_confirmation_steps_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-next-steps -->",
                "<!-- END GENERATED: failure-guide-stage-confirmation-next-steps -->",
                "- 改阶段顺序、缺失阶段、回环关系、人工拍板点",
                "- stage confirmation prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_validate_repo_docs_reports_failure_guide_blueprint_inspect_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-blueprint-inspect -->",
                "<!-- END GENERATED: failure-guide-blueprint-inspect -->",
                "- 必要时先跑一次下方 blueprint 校验命令",
                "- blueprint inspect prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_render_operator_command_docs_check_reports_failure_guide_release_next_steps_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-release-next-steps -->",
                "<!-- END GENERATED: failure-guide-release-next-steps -->",
                "5. 修完后只重跑对应命令，确认绿了再重跑总检查",
                "5. release next-step prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_failure_guide_new_text_block_drifts(self) -> None:
        cases = [
            (
                "<!-- BEGIN GENERATED: failure-guide-personal-empty-next-steps -->",
                "<!-- END GENERATED: failure-guide-personal-empty-next-steps -->",
                "- 先补访谈内容",
                "- personal empty next-step prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-next-interview-next-steps -->",
                "<!-- END GENERATED: failure-guide-next-interview-next-steps -->",
                "- 如果只是想先放行，确认当前流程是否允许临时 accept",
                "- next interview next-step prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-eval-draft-next-steps -->",
                "<!-- END GENERATED: failure-guide-eval-draft-next-steps -->",
                "- 按失败项回到对应访谈或画像文件补料",
                "- eval draft next-step prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-blueprint-reasons -->",
                "<!-- END GENERATED: failure-guide-blueprint-reasons -->",
                "- 阶段动作、工具映射、切换规则还是空",
                "- blueprint reasons prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-blueprint-next-steps -->",
                "<!-- END GENERATED: failure-guide-blueprint-next-steps -->",
                "- 再重建 blueprint",
                "- blueprint next-step prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: failure-guide-runtime-next-steps -->",
                "<!-- END GENERATED: failure-guide-runtime-next-steps -->",
                "- 补一条新的人工输入",
                "- runtime next-step prose drift injected",
            ),
        ]

        for start_marker, end_marker, original, replacement in cases:
            with self.subTest(start_marker=start_marker):
                fixture_root = self.copy_repo_docs_fixture()
                failure_guide = fixture_root / "references" / "failure_path_guide.md"
                failure_guide.write_text(
                    replace_in_marked_block(
                        failure_guide.read_text(encoding="utf-8"),
                        start_marker,
                        end_marker,
                        original,
                        replacement,
                    ),
                    encoding="utf-8",
                )

                proc = subprocess.run(
                    [
                        "python3",
                        str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                        "--check",
                    ],
                    cwd=fixture_root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_failure_guide_runtime_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-runtime-commands -->",
                "<!-- END GENERATED: failure-guide-runtime-commands -->",
                "`python3 scripts/run_workflow_turn.py --workflow-blueprint /tmp/my-workflow-runtime/workflow_blueprint.md --state /tmp/my-workflow-runtime/workflow_task_state.yaml --input \"继续推进下一步\" --output-dir /tmp/my-workflow-runtime/turn-output --execute-safe`",
                "`python3 scripts/run_workflow_turn_missing.py --workflow-blueprint /tmp/my-workflow-runtime/workflow_blueprint.md --state /tmp/my-workflow-runtime/workflow_task_state.yaml --input \"继续推进下一步\" --output-dir /tmp/my-workflow-runtime/turn-output --execute-safe`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_failure_guide_latest_stack_inspect_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-latest-stack-inspect -->",
                "<!-- END GENERATED: failure-guide-latest-stack-inspect -->",
                "- 必要时先跑一次下方 explain 命令",
                "- latest stack inspect prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_validate_repo_docs_reports_failure_guide_latest_stack_next_steps_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-latest-stack-next-steps -->",
                "<!-- END GENERATED: failure-guide-latest-stack-next-steps -->",
                "- 再看 rejection summary 是 bundle / pipeline / runtime / skill 哪一层在拦",
                "- latest-stack next-step prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_render_operator_command_docs_check_reports_failure_guide_quick_reference_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            failure_guide.read_text(encoding="utf-8").replace(
                "release report JSON、`compact_summary`、`release-logs/`",
                "release report missing",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/failure_path_guide.md", proc.stderr)

    def test_validate_repo_docs_reports_failure_guide_reading_order_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        failure_guide = fixture_root / "references" / "failure_path_guide.md"
        failure_guide.write_text(
            replace_in_marked_block(
                failure_guide.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: failure-guide-reading-order -->",
                "<!-- END GENERATED: failure-guide-reading-order -->",
                "3. 如果是 operator 问题，再看 [operator_playbook.md]",
                "3. reading order prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["failure_guide_render_mismatch"])

    def test_validate_repo_docs_reports_new_maintainer_map_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        new_maintainer = fixture_root / "references" / "new_maintainer_first_15_minutes.md"
        new_maintainer.write_text(
            new_maintainer.read_text(encoding="utf-8").replace(
                "1. [doc_router.md]",
                "1. [doc_router_missing.md]",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["new_maintainer_operator_render_mismatch"])

    def test_validate_repo_docs_reports_new_maintainer_text_block_render_mismatches(self) -> None:
        cases = [
            (
                "<!-- BEGIN GENERATED: new-maintainer-map-goals -->",
                "<!-- END GENERATED: new-maintainer-map-goals -->",
                "- 如果失败，日志和下一步一般看哪里",
                "- new maintainer map goals prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: new-maintainer-confirm -->",
                "<!-- END GENERATED: new-maintainer-confirm -->",
                "- `validate release-readiness` 能把文档校验、sample rebuild、blueprint gate、doctor/validate/explain 收进同一份总报告",
                "- new maintainer confirm prose drift injected",
            ),
            (
                "<!-- BEGIN GENERATED: new-maintainer-after-15 -->",
                "<!-- END GENERATED: new-maintainer-after-15 -->",
                "- 接下来该继续修文档、修 sample stack，还是修 operator/validator",
                "- new maintainer after-15 prose drift injected",
            ),
        ]

        for start_marker, end_marker, original, replacement in cases:
            with self.subTest(start_marker=start_marker):
                fixture_root = self.copy_repo_docs_fixture()
                new_maintainer = fixture_root / "references" / "new_maintainer_first_15_minutes.md"
                new_maintainer.write_text(
                    replace_in_marked_block(
                        new_maintainer.read_text(encoding="utf-8"),
                        start_marker,
                        end_marker,
                        original,
                        replacement,
                    ),
                    encoding="utf-8",
                )

                proc = subprocess.run(
                    [
                        "python3",
                        str(fixture_root / "scripts" / "validate_repo_docs.py"),
                        "--repo-root",
                        str(fixture_root),
                        "--format",
                        "json",
                    ],
                    cwd=fixture_root,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(proc.returncode, 0)
                report = read_json(proc.stdout)
                self.assertFalse(report["ok"])
                self.assertTrue(report["new_maintainer_operator_render_mismatch"])

    def test_render_operator_command_docs_check_reports_new_maintainer_failure_block_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        new_maintainer = fixture_root / "references" / "new_maintainer_first_15_minutes.md"
        new_maintainer.write_text(
            replace_in_marked_block(
                new_maintainer.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: new-maintainer-failure-steps -->",
                "<!-- END GENERATED: new-maintainer-failure-steps -->",
                "- 如果你只想快定位，不想重读整套文档，直接回 [failure_path_guide.md]",
                "- new maintainer failure prose drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/new_maintainer_first_15_minutes.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_release_checklist_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        checklist = fixture_root / "RELEASE_READINESS_CHECKLIST.md"
        checklist.write_text(
            checklist.read_text(encoding="utf-8").replace(
                "--summary-json /tmp/latest-stack-validate-summary.json",
                "--summary-json /tmp/latest-stack-validate-missing.json",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("RELEASE_READINESS_CHECKLIST.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_operator_playbook_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        playbook = fixture_root / "references" / "operator_playbook.md"
        playbook.write_text(
            playbook.read_text(encoding="utf-8").replace(
                "- 只做 latest-stack 校验：",
                "- 只做 latest stack missing：",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/operator_playbook.md", proc.stderr)

    def test_validate_repo_docs_reports_operator_playbook_refresh_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        playbook = fixture_root / "references" / "operator_playbook.md"
        playbook.write_text(
            playbook.read_text(encoding="utf-8").replace(
                "refresh_workflow_runtime_bundle.py --manifest /tmp/my-workflow-runtime/workflow_runtime_manifest.json",
                "refresh_workflow_runtime_bundle.py --manifest /tmp/runtime-missing.json",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["operator_playbook_render_mismatch"])

    def test_render_operator_command_docs_check_reports_operator_playbook_release_behavior_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        playbook = fixture_root / "references" / "operator_playbook.md"
        playbook.write_text(
            replace_in_marked_block(
                playbook.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: operator-playbook-release-behavior -->",
                "<!-- END GENERATED: operator-playbook-release-behavior -->",
                "- 原始 explain 里的 `candidate_rejections` 现在也会压成单行非零摘要；如果所有类别都是 `0`，该段会直接省略",
                "- operator playbook release behavior drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/operator_playbook.md", proc.stderr)

    def test_validate_repo_docs_reports_new_maintainer_operator_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        new_maintainer = fixture_root / "references" / "new_maintainer_first_15_minutes.md"
        new_maintainer.write_text(
            new_maintainer.read_text(encoding="utf-8").replace(
                "2. `python3 scripts/clone_ops.py doctor latest-stack --explain --summary-json /tmp/latest-stack-summary.json`",
                "2. `python3 scripts/clone_ops.py doctor latest stack missing`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["new_maintainer_operator_render_mismatch"])

    def test_render_operator_command_docs_check_reports_current_flow_entry_choice_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            current_flow.read_text(encoding="utf-8").replace(
                "`scripts/refresh_workflow_runtime_bundle.py`",
                "`scripts/refresh_runtime_missing.py`",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/current_system_flow.md", proc.stderr)

    def test_validate_repo_docs_reports_current_flow_workflow_file_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            current_flow.read_text(encoding="utf-8").replace(
                "用它跑 `refresh_workflow_runtime_bundle.py`，或核对 runtime provenance",
                "runtime next step missing",
                1,
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["current_flow_render_mismatch"])

    def test_validate_repo_docs_reports_current_flow_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            current_flow.read_text(encoding="utf-8").replace(
                "`doctor latest-stack --explain`",
                "`doctor latest stack missing`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["current_flow_render_mismatch"])

    def test_render_operator_command_docs_check_reports_current_flow_pipeline_resume_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-pipeline-resume -->",
                "<!-- END GENERATED: current-flow-pipeline-resume -->",
                "`python3 scripts/refresh_workflow_blueprint_pipeline.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json`",
                "`python3 scripts/refresh_workflow_pipeline_missing.py --manifest /tmp/my-workflow-pipeline/workflow_blueprint_pipeline_manifest.json`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/current_system_flow.md", proc.stderr)

    def test_render_operator_command_docs_check_reports_current_flow_persona_resume_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-persona-resume -->",
                "<!-- END GENERATED: current-flow-persona-resume -->",
                "`python3 scripts/refresh_working_clone_bundle.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
                "`python3 scripts/refresh_working_clone_bundle_missing.py --manifest /tmp/my-clone-bundle/working_clone_bundle_manifest.json`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/current_system_flow.md", proc.stderr)

    def test_validate_repo_docs_reports_current_flow_runtime_resume_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-runtime-resume -->",
                "<!-- END GENERATED: current-flow-runtime-resume -->",
                "`python3 scripts/run_workflow_until_stop.py --workflow-blueprint /tmp/my-workflow-runtime/workflow_blueprint.md --state /tmp/my-workflow-runtime/workflow_task_state.yaml --initial-input \"继续推进直到需要人工介入\" --output-dir /tmp/my-workflow-runtime/until-stop-output --execute-safe`",
                "`python3 scripts/run_workflow_until_stop_missing.py --workflow-blueprint /tmp/my-workflow-runtime/workflow_blueprint.md --state /tmp/my-workflow-runtime/workflow_task_state.yaml --initial-input \"继续推进直到需要人工介入\" --output-dir /tmp/my-workflow-runtime/until-stop-output --execute-safe`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["current_flow_render_mismatch"])

    def test_render_operator_command_docs_check_reports_current_flow_operator_resume_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-operator-resume -->",
                "<!-- END GENERATED: current-flow-operator-resume -->",
                "`doctor / validate / explain`",
                "`doctor / validate / inspect`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/current_system_flow.md", proc.stderr)

    def test_validate_repo_docs_reports_current_flow_persona_stops_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-persona-stops -->",
                "<!-- END GENERATED: current-flow-persona-stops -->",
                "- 访谈还空白：停在 `personal_interview.md`",
                "- 人格层停点漂移 injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["current_flow_render_mismatch"])

    def test_render_operator_command_docs_check_reports_current_flow_operator_stops_drift(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-operator-stops -->",
                "<!-- END GENERATED: current-flow-operator-stops -->",
                "- release-readiness 已执行：停在 release report、失败日志或 compact summary",
                "- operator 停点漂移 injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "render_operator_command_docs.py"),
                "--check",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("references/current_system_flow.md", proc.stderr)

    def test_validate_repo_docs_reports_current_flow_persona_files_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-persona-files -->",
                "<!-- END GENERATED: current-flow-persona-files -->",
                "| `working_clone_bundle_manifest.json` | `<bundle-root>/working_clone_bundle_manifest.json` | `bootstrap_working_clone_bundle.py` | working bundle 的主清单，也是后续 refresh 的入口 | 用它跑 `refresh_working_clone_bundle.py` 或 `run_working_clone_until_final.py` |",
                "| `working_clone_bundle_manifest.json` | `<bundle-root>/working_clone_bundle_manifest.json` | `bootstrap_working_clone_bundle.py` | persona file drift injected | 用它跑 `refresh_working_clone_bundle.py` 或 `run_working_clone_until_final.py` |",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["current_flow_render_mismatch"])

    def test_validate_repo_docs_reports_current_flow_operator_files_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        current_flow = fixture_root / "references" / "current_system_flow.md"
        current_flow.write_text(
            replace_in_marked_block(
                current_flow.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: current-flow-operator-files -->",
                "<!-- END GENERATED: current-flow-operator-files -->",
                "| `SAMPLE_STACK_SUMMARY.json` | `<sample-root>/SAMPLE_STACK_SUMMARY.json` | `rebuild_sample_stack.py` | sample stack 已重建完成，可用于 sample/current/latest 校验 | 跑 `doctor sample-stack` 或继续 release-readiness |",
                "| `SAMPLE_STACK_SUMMARY.json` | `<sample-root>/SAMPLE_STACK_SUMMARY.json` | `rebuild_sample_stack.py` | operator file drift injected | 跑 `doctor sample-stack` 或继续 release-readiness |",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["current_flow_render_mismatch"])

    def test_validate_repo_docs_reports_capability_index_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        capability_index = fixture_root / "references" / "capability_index.md"
        capability_index.write_text(
            capability_index.read_text(encoding="utf-8").replace(
                "- `scripts/stack_discovery.py`",
                "- `scripts/stack-discovery-missing.py`",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["capability_index_render_mismatch"])

    def test_validate_repo_docs_reports_capability_index_recent_release_behavior_render_mismatch(self) -> None:
        fixture_root = self.copy_repo_docs_fixture()
        capability_index = fixture_root / "references" / "capability_index.md"
        capability_index.write_text(
            replace_in_marked_block(
                capability_index.read_text(encoding="utf-8"),
                "<!-- BEGIN GENERATED: capability-index-recent-release-behavior -->",
                "<!-- END GENERATED: capability-index-recent-release-behavior -->",
                "- 成功的 `explain latest-stack` 摘要现在会额外输出一条 `refresh_hotspots:`，帮助维护者直接扫描最近 refresh churn 的主因",
                "- capability index recent release behavior drift injected",
            ),
            encoding="utf-8",
        )

        proc = subprocess.run(
            [
                "python3",
                str(fixture_root / "scripts" / "validate_repo_docs.py"),
                "--repo-root",
                str(fixture_root),
                "--format",
                "json",
            ],
            cwd=fixture_root,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        report = read_json(proc.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(report["capability_index_render_mismatch"])


if __name__ == "__main__":
    unittest.main()
