from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import rebuild_sample_stack
from scripts import run_release_readiness


REPO_ROOT = Path(__file__).resolve().parents[1]


class StackOperatorFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="mind-clone-ops-")
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

    def patch_repo_file(self, path: Path, marker: str) -> None:
        original = path.read_text(encoding="utf-8")
        self.addCleanup(path.write_text, original, encoding="utf-8")
        path.write_text(original.rstrip() + f"\n\n{marker}\n", encoding="utf-8")

    def copy_example_inputs(self) -> dict[str, Path]:
        examples = REPO_ROOT / "examples" / "ai_engineer"
        input_root = self.root / "custom-inputs"
        input_root.mkdir(parents=True, exist_ok=True)
        copied: dict[str, Path] = {}
        for name in [
            "interview_filled.md",
            "workflow_interview_filled.md",
            "mind_profile.md",
            "system_prompt.md",
            "eval_report.md",
            "research_digest.md",
        ]:
            destination = input_root / name
            destination.write_text((examples / name).read_text(encoding="utf-8"), encoding="utf-8")
            copied[name] = destination
        return copied

    def build_custom_working_bundle(self, output_dir: Path) -> dict[str, Path]:
        copied = self.copy_example_inputs()
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--interview",
            str(copied["interview_filled.md"]),
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--mind-profile",
            str(copied["mind_profile.md"]),
            "--system-prompt",
            str(copied["system_prompt.md"]),
            "--eval-report",
            str(copied["eval_report.md"]),
            "--research-digest",
            str(copied["research_digest.md"]),
            "--workflow-name",
            "AI工程需求实现蓝图",
            "--work-unit",
            "接到一个新 AI 需求后完成首版实现",
            "--known-context",
            "AI工程师分身 / AI Engineer",
            "--workflow-interview",
            str(copied["workflow_interview_filled.md"]),
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)
        return copied

    def test_build_repo_docs_summary_counts_generated_doc_render_drift(self) -> None:
        summary = run_release_readiness.build_repo_docs_summary(
            {
                "ok": False,
                "missing_docs": [],
                "release_checklist_missing_patterns": [],
                "readme_missing_patterns": [],
                "current_flow_missing_patterns": [],
                "capability_index_missing_patterns": [],
                "operator_playbook_missing_patterns": [],
                "operator_command_contract_missing_patterns": [],
                "operator_command_summary_missing_patterns": [],
                "failure_guide_missing_patterns": [],
                "glossary_missing_terms": [],
                "example_index_missing_patterns": [],
                "doc_router_missing_patterns": [],
                "new_maintainer_missing_patterns": [],
                "release_readiness_order_issues": [],
                "capability_index_render_mismatch": True,
                "release_checklist_render_mismatch": True,
                "current_flow_render_mismatch": True,
                "readme_operator_render_mismatch": True,
                "operator_playbook_render_mismatch": True,
                "new_maintainer_operator_render_mismatch": True,
                "doc_router_render_mismatch": True,
                "failure_guide_render_mismatch": True,
                "operator_command_contract_render_mismatch": False,
                "operator_command_summary_render_mismatch": True,
                "missing_script_refs": [],
                "missing_example_files": [],
            }
        )
        self.assertEqual(summary["headline"], "repo docs validation failed")
        self.assertIn("release_checklist=0", summary["details"][0])
        self.assertIn("operator_render=9", summary["details"][0])

    def test_working_bundle_can_track_persona_plus_workflow_before_work_unit_is_defined(self) -> None:
        copied = self.copy_example_inputs()
        output_dir = self.root / "bundle-with-workflow-target"
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--interview",
            str(copied["interview_filled.md"]),
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--mind-profile",
            str(copied["mind_profile.md"]),
            "--system-prompt",
            str(copied["system_prompt.md"]),
            "--eval-report",
            str(copied["eval_report.md"]),
            "--research-digest",
            str(copied["research_digest.md"]),
            "--target-mode",
            "persona-plus-workflow",
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)

        manifest = json.loads((output_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        validation = json.loads((output_dir / "working_clone_bundle_validation.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["target_mode"], "persona-plus-workflow")
        self.assertEqual(manifest["refresh_dependency_groups"], ["bundle_core", "workflow_shared"])
        self.assertTrue(manifest["steps"]["workflow_enabled"])
        self.assertFalse(manifest["steps"]["workflow_target_defined"])
        self.assertTrue((output_dir / "workflow_interview.md").exists())
        self.assertIn("workflow_target", {item["item"] for item in validation["blockers"]})
        bundle_readme = (output_dir / "WORKING_CLONE_BUNDLE_README.md").read_text(encoding="utf-8")
        self.assertIn("## User View", bundle_readme)
        self.assertIn("## Operator View", bundle_readme)
        self.assertIn("status: 人格层已交付，workflow 轨道已开启，等待确认第一类典型工作", bundle_readme)
        self.assertIn("persona_usage_now: 人格层分身已经可用。", bundle_readme)
        self.assertIn("workflow_usage_now: workflow 轨道已开启，但还在等第一类典型工作。", bundle_readme)

    def test_working_bundle_can_infer_workflow_target_from_existing_interview(self) -> None:
        copied = self.copy_example_inputs()
        output_dir = self.root / "bundle-with-inferred-work-unit"
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--interview",
            str(copied["interview_filled.md"]),
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--mind-profile",
            str(copied["mind_profile.md"]),
            "--system-prompt",
            str(copied["system_prompt.md"]),
            "--eval-report",
            str(copied["eval_report.md"]),
            "--research-digest",
            str(copied["research_digest.md"]),
            "--target-mode",
            "persona-plus-workflow",
            "--workflow-interview",
            str(copied["workflow_interview_filled.md"]),
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)

        manifest = json.loads((output_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        pipeline_manifest = json.loads(
            (output_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json").read_text(encoding="utf-8")
        )
        runtime_manifest = json.loads(
            (
                output_dir / "workflow-blueprint-pipeline" / "workflow-runtime-bundle" / "workflow_runtime_manifest.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["work_unit"], "接到一个新 AI 需求后完成首版实现")
        self.assertEqual(manifest["refresh_dependency_groups"], ["bundle_core", "workflow_shared"])
        self.assertEqual(pipeline_manifest["refresh_dependency_groups"], ["workflow_shared"])
        self.assertEqual(runtime_manifest["refresh_dependency_groups"], ["workflow_shared", "runtime_core"])
        self.assertTrue(manifest["steps"]["workflow_enabled"])
        self.assertTrue(manifest["steps"]["workflow_target_defined"])
        self.assertTrue(manifest["steps"]["workflow_pipeline"])
        self.assertTrue(manifest["steps"]["workflow_clone_skill"])
        self.assertTrue(manifest["steps"]["workflow_runtime_bundle"])
        pipeline_readme = (
            output_dir / "workflow-blueprint-pipeline" / "WORKFLOW_BLUEPRINT_PIPELINE_README.md"
        ).read_text(encoding="utf-8")
        runtime_readme = (
            output_dir / "workflow-blueprint-pipeline" / "workflow-runtime-bundle" / "WORKFLOW_RUNTIME_README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## User View", pipeline_readme)
        self.assertIn("## Operator View", pipeline_readme)
        self.assertIn("## User View", runtime_readme)
        self.assertIn("## Operator View", runtime_readme)

    def test_refresh_working_bundle_compiles_workflow_after_target_is_filled(self) -> None:
        copied = self.copy_example_inputs()
        output_dir = self.root / "bundle-refresh-after-target"
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--interview",
            str(copied["interview_filled.md"]),
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--mind-profile",
            str(copied["mind_profile.md"]),
            "--system-prompt",
            str(copied["system_prompt.md"]),
            "--eval-report",
            str(copied["eval_report.md"]),
            "--research-digest",
            str(copied["research_digest.md"]),
            "--target-mode",
            "persona-plus-workflow",
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)

        bundle_workflow_interview = output_dir / "workflow_interview.md"
        bundle_workflow_interview.write_text(
            copied["workflow_interview_filled.md"].read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        refresh = self.run_cmd(
            "scripts/refresh_working_clone_bundle.py",
            "--manifest",
            str(output_dir / "working_clone_bundle_manifest.json"),
        )
        self.assertEqual(refresh.returncode, 0, refresh.stderr)

        manifest = json.loads((output_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        validation = json.loads((output_dir / "working_clone_bundle_validation.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["work_unit"], "接到一个新 AI 需求后完成首版实现")
        self.assertTrue(manifest["steps"]["workflow_target_defined"])
        self.assertTrue(manifest["steps"]["workflow_pipeline"])
        self.assertTrue(manifest["steps"]["workflow_clone_skill"])
        self.assertTrue(manifest["steps"]["workflow_runtime_bundle"])
        self.assertNotIn("workflow_target", {item["item"] for item in validation["blockers"]})
        self.assertTrue((output_dir / "workflow-blueprint-pipeline" / "workflow_blueprint.md").exists())

    def test_empty_start_bundle_can_bootstrap_both_interviews_then_compile_full_workflow(self) -> None:
        copied = self.copy_example_inputs()
        output_dir = self.root / "bundle-empty-start"
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--target-mode",
            "persona-plus-workflow",
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)

        personal_interview = output_dir / "personal_interview.md"
        workflow_interview = output_dir / "workflow_interview.md"
        self.assertTrue(personal_interview.exists())
        self.assertTrue(workflow_interview.exists())

        manifest = json.loads((output_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["steps"]["personal_interview_ready"])
        self.assertFalse(manifest["steps"]["personal_clone_skill"])
        self.assertTrue(manifest["steps"]["workflow_enabled"])
        self.assertFalse(manifest["steps"]["workflow_target_defined"])
        self.assertFalse((output_dir / "DELIVERY_SUMMARY.md").exists())

        personal_interview.write_text(copied["interview_filled.md"].read_text(encoding="utf-8"), encoding="utf-8")
        workflow_interview.write_text(copied["workflow_interview_filled.md"].read_text(encoding="utf-8"), encoding="utf-8")

        refresh = self.run_cmd(
            "scripts/refresh_working_clone_bundle.py",
            "--manifest",
            str(output_dir / "working_clone_bundle_manifest.json"),
        )
        self.assertEqual(refresh.returncode, 0, refresh.stderr)

        manifest = json.loads((output_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["steps"]["personal_interview_ready"])
        self.assertTrue(manifest["steps"]["personal_clone_skill"])
        self.assertTrue(manifest["steps"]["workflow_target_defined"])
        self.assertTrue(manifest["steps"]["workflow_pipeline"])
        self.assertTrue(manifest["steps"]["workflow_clone_skill"])
        self.assertTrue(manifest["steps"]["workflow_runtime_bundle"])
        self.assertTrue((output_dir / "workflow-blueprint-pipeline" / "workflow_blueprint.md").exists())
        self.assertTrue((output_dir / "workflow-blueprint-pipeline" / "workflow-clone-skill" / "SKILL.md").exists())
        self.assertTrue(
            (
                output_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow-clone-runtime"
                / "SKILL.md"
            ).exists()
        )
        self.assertTrue((output_dir / "DELIVERY_SUMMARY.md").exists())
        self.assertTrue((output_dir / "personal-clone-skill" / "DELIVERY_SUMMARY.md").exists())

    def test_render_delivery_summary_includes_workflow_bundle_status(self) -> None:
        copied = self.copy_example_inputs()
        output_dir = self.root / "bundle-delivery-summary"
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--interview",
            str(copied["interview_filled.md"]),
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--mind-profile",
            str(copied["mind_profile.md"]),
            "--system-prompt",
            str(copied["system_prompt.md"]),
            "--eval-report",
            str(copied["eval_report.md"]),
            "--research-digest",
            str(copied["research_digest.md"]),
            "--target-mode",
            "persona-plus-workflow",
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)

        summary = self.run_cmd(
            "scripts/render_delivery_summary.py",
            "--input",
            str(output_dir / "personal-clone-skill" / "clone_config.yaml"),
            "--format",
            "json",
        )
        self.assertEqual(summary.returncode, 0, summary.stderr)
        payload = json.loads(summary.stdout)

        bundle_summary = output_dir / "DELIVERY_SUMMARY.md"
        personal_summary = output_dir / "personal-clone-skill" / "DELIVERY_SUMMARY.md"
        self.assertTrue(bundle_summary.exists())
        self.assertTrue(personal_summary.exists())
        self.assertIn("- 当前状态：`draft`", bundle_summary.read_text(encoding="utf-8"))
        self.assertIn("- working bundle 状态：`draft`", personal_summary.read_text(encoding="utf-8"))

        self.assertEqual(payload["workflow"]["target_mode"], "persona-plus-workflow")
        self.assertFalse(payload["workflow"]["workflow_target_defined"])
        self.assertEqual(payload["draft_status"], "draft")
        self.assertEqual(payload["persona_draft_status"], "final")
        self.assertEqual(payload["workflow"]["bundle_recommended_release"], "draft")
        self.assertEqual(payload["workflow"]["workflow_state"], "已开启 workflow 轨道，等待确认第一类典型工作")
        self.assertTrue(any("workflow_target" in item for item in payload["workflow"]["blockers"]))
        self.assertIn("workflow_interview.md", payload["workflow"]["workflow_interview"])

    def test_render_delivery_summary_marks_persona_final_but_bundle_draft(self) -> None:
        copied = self.copy_example_inputs()
        output_dir = self.root / "bundle-delivery-summary-markdown"
        build = self.run_cmd(
            "scripts/bootstrap_working_clone_bundle.py",
            "--interview",
            str(copied["interview_filled.md"]),
            "--output-dir",
            str(output_dir),
            "--name",
            "AI工程师分身",
            "--profession",
            "AI Engineer",
            "--timestamp",
            rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP,
            "--mind-profile",
            str(copied["mind_profile.md"]),
            "--system-prompt",
            str(copied["system_prompt.md"]),
            "--eval-report",
            str(copied["eval_report.md"]),
            "--research-digest",
            str(copied["research_digest.md"]),
            "--target-mode",
            "persona-plus-workflow",
            "--execute-safe",
        )
        self.assertEqual(build.returncode, 0, build.stderr)

        summary = self.run_cmd(
            "scripts/render_delivery_summary.py",
            "--input",
            str(output_dir / "personal-clone-skill" / "clone_config.yaml"),
        )
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertIn("人格层已达到 final 标准，但整体 working bundle 仍是 draft", summary.stdout)
        self.assertIn("- 当前状态：`draft`", summary.stdout)
        self.assertIn("- 人格层状态：`final`", summary.stdout)
        self.assertIn("- working bundle 状态：`draft`", summary.stdout)

    def test_release_readiness_log_retention_helpers(self) -> None:
        self.assertFalse(run_release_readiness.should_write_log(0, "", keep_success_logs=False))
        self.assertFalse(run_release_readiness.should_write_log(0, "ok", keep_success_logs=False))
        self.assertTrue(run_release_readiness.should_write_log(0, "ok", keep_success_logs=True))
        self.assertTrue(run_release_readiness.should_write_log(1, "failure", keep_success_logs=False))

    def test_write_log_creates_logs_dir_lazily(self) -> None:
        logs_dir = self.root / "release-logs"
        self.assertFalse(logs_dir.exists())
        empty_log = run_release_readiness.write_log(logs_dir, "unit_tests", "stdout", "")
        self.assertEqual(empty_log, "")
        self.assertFalse(logs_dir.exists())

        written = run_release_readiness.write_log(logs_dir, "unit_tests", "stdout", "ok\n")
        self.assertTrue(written)
        self.assertTrue(logs_dir.exists())
        self.assertTrue(Path(written).exists())

    def test_render_text_compacts_success_steps_and_keeps_failure_context(self) -> None:
        report = {
            "output_root": "/tmp/sample-release",
            "sample_summary": "/tmp/sample-release/SAMPLE_STACK_SUMMARY.json",
            "logs_dir": "/tmp/sample-release/release-logs",
            "ok": False,
            "steps": [
                {
                    "label": "unit_tests",
                    "ok": True,
                    "exit_code": 0,
                    "command": ["python3", "-m", "unittest"],
                    "compact_summary": {
                        "headline": "unit tests passed",
                        "details": ["suite: 13 tests in 12.3s"],
                    },
                    "stdout_preview": "",
                    "stderr_preview": "",
                    "stdout_log_path": "",
                    "stderr_log_path": "",
                    "summary_json_path": "",
                },
                {
                    "label": "validate_latest_stack",
                    "ok": False,
                    "exit_code": 1,
                    "command": ["python3", "scripts/clone_ops.py", "validate", "latest-stack"],
                    "compact_summary": {
                        "headline": "latest stack validation: 7/9 checks passed; 2 failed",
                        "details": [
                            "selection: latest_coherent_stack",
                            "failed checks: cross-artifact linkage, workflow skill release",
                        ],
                    },
                    "stdout_preview": "trimmed stdout",
                    "stderr_preview": "trimmed stderr",
                    "stdout_log_path": "/tmp/sample-release/release-logs/validate_latest_stack.stdout.log",
                    "stderr_log_path": "/tmp/sample-release/release-logs/validate_latest_stack.stderr.log",
                    "summary_json_path": "/tmp/sample-release/release_validate_latest_stack.json",
                },
            ],
        }

        rendered = run_release_readiness.render_text(report)

        self.assertIn("# release_readiness", rendered)
        self.assertIn("overall: fail", rendered)
        self.assertIn("- ok unit_tests: unit tests passed", rendered)
        self.assertIn("details: suite: 13 tests in 12.3s", rendered)
        self.assertNotIn("command: python3 -m unittest", rendered)
        self.assertIn("- fail validate_latest_stack: latest stack validation: 7/9 checks passed; 2 failed", rendered)
        self.assertIn("command: python3 scripts/clone_ops.py validate latest-stack", rendered)
        self.assertIn("stdout: trimmed stdout", rendered)
        self.assertIn("stderr: trimmed stderr", rendered)

    def test_build_rebuild_summary_drops_success_signature_noise(self) -> None:
        summary = run_release_readiness.build_rebuild_summary(
            {
                "bundle_dir": "/tmp/sample-stack/working-clone-bundle",
                "stack": {
                    "selection_mode": "sample_stack_build",
                    "bundle_dir": "/tmp/sample-stack/working-clone-bundle",
                    "pipeline_dir": "/tmp/sample-stack/workflow-blueprint-pipeline",
                    "runtime_dir": "/tmp/sample-stack/workflow-runtime-bundle",
                    "signatures": {
                        "bundle": {
                            "clone_config_hash": "abc123456789xyz",
                            "workflow_blueprint_hash": "def987654321xyz",
                        }
                    },
                },
                "latest_tmp_exports": {
                    "version": "12",
                    "bundle_dir": "/tmp/working-clone-bundle-v12",
                    "pipeline_dir": "/tmp/workflow-blueprint-pipeline-v12",
                    "runtime_dir": "/tmp/workflow-runtime-v12",
                    "personal_skill_dir": "/tmp/personal-clone-skill-v12",
                    "workflow_skill_dir": "/tmp/workflow-clone-skill-v12",
                },
                "tmp_retention": {
                    "report": {"retain": 5, "prunable_total": 20},
                    "pruned": {},
                },
                "validation": {"ok": True, "checks": {"cross_artifact_linkage": {"ok": True}}},
            }
        )

        self.assertEqual(summary["headline"], "sample stack rebuilt and validated")
        self.assertIn(
            "stack_ref: sample_stack_build | bundle=working-clone-bundle | pipeline=workflow-blueprint-pipeline | runtime=workflow-runtime-bundle",
            summary["details"],
        )
        self.assertFalse(any(detail.startswith("bundle:") for detail in summary["details"]))
        self.assertFalse(any(detail.startswith("signatures:") for detail in summary["details"]))

    def test_build_validation_step_summary_keeps_signatures_only_for_latest_explain(self) -> None:
        payload = {
            "ok": True,
            "checks": {
                "personal_skill_release": {
                    "ok": True,
                    "current_draft_status": "final",
                    "recommended_draft_status": "final",
                    "release_valid": True,
                }
            },
        }
        selection_summary = {
            "selection_mode": "sample_stack_summary",
            "bundle_dir": "/tmp/working-clone-bundle",
            "pipeline_dir": "/tmp/workflow-blueprint-pipeline",
            "runtime_dir": "/tmp/workflow-runtime",
            "signatures": {
                "bundle": {
                    "clone_config_hash": "abc123456789xyz",
                    "workflow_blueprint_hash": "def987654321xyz",
                }
            },
            "discovery_report": {
                "cohort_alignment": {
                    "target_version": 129,
                    "versions": {"pipeline": 129},
                },
                "freshness": {
                    "categories": {
                        "pipeline": {"freshness_status": "aligned_selection"},
                    },
                    "warnings": [],
                    "notes": [
                        "pipeline: kept workflow-blueprint-pipeline-v129 to align with cohort target v129 instead of newer matching candidates (workflow-blueprint-pipeline-v130)"
                    ],
                }
            },
            "refresh_stats": {
                "bundle": {
                    "history_count": 2,
                    "top_groups": [{"value": "bundle_core", "count": 2}],
                    "top_classes": [{"value": "content_changed", "count": 2}],
                    "top_files": [{"value": "build_personal_clone_skill.py", "count": 1}],
                },
                "pipeline": {
                    "history_count": 1,
                    "top_groups": [{"value": "workflow_shared", "count": 1}],
                    "top_classes": [{"value": "content_changed", "count": 1}],
                    "top_files": [{"value": "build_workflow_blueprint.py", "count": 1}],
                },
            },
        }

        local_summary = run_release_readiness.build_validation_step_summary(
            "doctor_sample_stack",
            payload,
            selection_summary,
        )
        latest_summary = run_release_readiness.build_validation_step_summary(
            "doctor_latest_stack",
            payload,
            selection_summary | {"selection_mode": "latest_coherent_stack"},
        )
        validate_latest_summary = run_release_readiness.build_validation_step_summary(
            "validate_latest_stack",
            payload,
            selection_summary | {"selection_mode": "latest_coherent_stack"},
        )
        explain_latest_summary = run_release_readiness.build_explain_step_summary(
            selection_summary | {"selection_mode": "latest_coherent_stack"},
            "",
            "",
            0,
        )

        self.assertFalse(any(detail.startswith("signatures:") for detail in local_summary["details"]))
        self.assertTrue(any(detail.startswith("release:") for detail in local_summary["details"]))
        self.assertFalse(any(detail.startswith("signatures:") for detail in latest_summary["details"]))
        self.assertFalse(any(detail.startswith("signatures:") for detail in validate_latest_summary["details"]))
        self.assertFalse(any(detail.startswith("freshness notes:") for detail in latest_summary["details"]))
        self.assertFalse(any(detail.startswith("freshness notes:") for detail in validate_latest_summary["details"]))
        self.assertTrue(any(detail.startswith("signatures:") for detail in explain_latest_summary["details"]))
        self.assertIn("freshness notes: aligned_to_v129=pipeline", explain_latest_summary["details"])
        self.assertTrue(any(detail.startswith("refresh_hotspots:") for detail in explain_latest_summary["details"]))

    def test_collect_stack_selection_details_summarizes_freshness_warnings(self) -> None:
        selection_summary = {
            "selection_mode": "latest_coherent_stack",
            "bundle_dir": "/tmp/working-clone-bundle-v129",
            "pipeline_dir": "/tmp/workflow-blueprint-pipeline-v129",
            "runtime_dir": "/tmp/workflow-runtime-v129",
            "discovery_report": {
                "freshness": {
                    "categories": {
                        "pipeline": {"freshness_status": "stale_same_signature"},
                        "runtime": {"freshness_status": "stale_same_signature"},
                        "workflow_skill": {"freshness_status": "current"},
                    },
                    "warnings": ["pipeline warning", "runtime warning"],
                    "notes": [],
                }
            },
        }

        details = run_release_readiness.collect_stack_selection_details(selection_summary)
        self.assertIn("freshness warnings: same_signature_newer=pipeline,runtime", details)

    def test_clone_ops_explain_latest_stack_prints_summary_once(self) -> None:
        summary_path = self.root / "latest-stack-summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "selection_mode": "latest_coherent_stack",
                    "bundle_dir": "/tmp/working-clone-bundle-v129",
                    "pipeline_dir": "/tmp/workflow-blueprint-pipeline-v129",
                    "runtime_dir": "/tmp/workflow-runtime-v129",
                    "personal_skill_dir": "/tmp/personal-clone-skill-v129",
                    "workflow_skill_dir": "/tmp/workflow-clone-skill-v129",
                    "discovery_report": {
                        "cohort_alignment": {"target_version": 129},
                        "rejection_counts": {
                            "bundle": 0,
                            "pipeline": 0,
                        },
                        "freshness": {
                            "categories": {
                                "pipeline": {"freshness_status": "aligned_selection"},
                            },
                            "warnings": [],
                            "notes": ["pipeline note"],
                        },
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cmd(
            "scripts/clone_ops.py",
            "explain",
            "latest-stack",
            "--stack-summary",
            str(summary_path),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.count("selection_mode: latest_coherent_stack"), 1)
        self.assertIn("freshness_notes: aligned_to_v129=pipeline", result.stdout)
        self.assertNotIn("candidate_rejections:", result.stdout)

    def test_clone_ops_explain_latest_stack_groups_rejected_candidate_reasons(self) -> None:
        summary_path = self.root / "latest-stack-summary-with-rejections.json"
        summary_path.write_text(
            json.dumps(
                {
                    "selection_mode": "latest_coherent_stack",
                    "bundle_dir": "/tmp/working-clone-bundle-v129",
                    "pipeline_dir": "/tmp/workflow-blueprint-pipeline-v129",
                    "runtime_dir": "/tmp/workflow-runtime-v129",
                    "personal_skill_dir": "/tmp/personal-clone-skill-v129",
                    "workflow_skill_dir": "/tmp/workflow-clone-skill-v129",
                    "discovery_report": {
                        "rejection_counts": {
                            "bundle": 0,
                            "pipeline": 3,
                        },
                        "candidate_reports": {
                            "pipeline": [
                                {
                                    "path": "/tmp/workflow-blueprint-pipeline-v131",
                                    "status": "validator_failed",
                                    "reason": "validator failed",
                                },
                                {
                                    "path": "/tmp/workflow-blueprint-pipeline-v130",
                                    "status": "validator_failed",
                                    "reason": "validator failed",
                                },
                                {
                                    "path": "/tmp/workflow-blueprint-pipeline-v129",
                                    "status": "missing_required_files",
                                    "reason": "missing workflow_blueprint_pipeline_manifest.json",
                                },
                            ]
                        },
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_cmd(
            "scripts/clone_ops.py",
            "explain",
            "latest-stack",
            "--stack-summary",
            str(summary_path),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("candidate_rejections: pipeline=3", result.stdout)
        self.assertIn(
            "pipeline_rejected_candidates: validator failed x2 (workflow-blueprint-pipeline-v131,workflow-blueprint-pipeline-v130); missing workflow_blueprint_pipeline_manifest.json x1 (workflow-blueprint-pipeline-v129)",
            result.stdout,
        )
        self.assertNotIn("pipeline_rejected_candidates:\n-", result.stdout)

    def test_select_text_details_keeps_freshness_notes_and_refresh_hotspots(self) -> None:
        details = run_release_readiness.select_text_details(
            [
                "stack_ref: latest_coherent_stack | bundle=working-clone-bundle-v138 | pipeline=workflow-blueprint-pipeline-v138 | runtime=workflow-runtime-v138",
                "signatures: clone=abc, blueprint=def",
                "freshness notes: aligned_to_v138=pipeline,runtime,personal,workflow",
                "refresh_hotspots: none",
            ],
            ok=True,
        )
        self.assertEqual(
            details,
            [
                "stack_ref: latest_coherent_stack | bundle=working-clone-bundle-v138 | pipeline=workflow-blueprint-pipeline-v138 | runtime=workflow-runtime-v138",
                "signatures: clone=abc, blueprint=def",
                "freshness notes: aligned_to_v138=pipeline,runtime,personal,workflow",
                "refresh_hotspots: none",
            ],
        )

    def test_tmp_retention_report_and_prune_helpers(self) -> None:
        tmp_root = self.root / "tmp-root"
        tmp_root.mkdir(parents=True, exist_ok=True)
        for version in [1, 2, 3]:
            (tmp_root / f"working-clone-bundle-v{version}").mkdir()
        for version in [2, 4]:
            (tmp_root / f"workflow-blueprint-pipeline-v{version}").mkdir()

        retention = rebuild_sample_stack.build_tmp_retention_report(retain=2, tmp_root=tmp_root)
        bundle_category = retention["categories"]["bundle_dir"]
        pipeline_category = retention["categories"]["pipeline_dir"]
        self.assertEqual(
            bundle_category["kept"],
            [
                str(tmp_root / "working-clone-bundle-v3"),
                str(tmp_root / "working-clone-bundle-v2"),
            ],
        )
        self.assertEqual(bundle_category["prunable"], [str(tmp_root / "working-clone-bundle-v1")])
        self.assertEqual(
            pipeline_category["kept"],
            [
                str(tmp_root / "workflow-blueprint-pipeline-v4"),
                str(tmp_root / "workflow-blueprint-pipeline-v2"),
            ],
        )

        pruned = rebuild_sample_stack.prune_tmp_exports(retention)
        self.assertEqual(pruned["bundle_dir"], [str((tmp_root / "working-clone-bundle-v1").resolve())])
        self.assertFalse((tmp_root / "working-clone-bundle-v1").exists())
        self.assertTrue((tmp_root / "working-clone-bundle-v3").exists())

    def test_export_latest_tmp_compat_retries_after_version_collision(self) -> None:
        tmp_root = self.root / "tmp-root"
        tmp_root.mkdir(parents=True, exist_ok=True)
        source_root = self.root / "sources"
        source_root.mkdir(parents=True, exist_ok=True)

        summary: dict[str, object] = {}
        for key in rebuild_sample_stack.COMPAT_EXPORT_PREFIXES:
            source_dir = source_root / key
            source_dir.mkdir(parents=True, exist_ok=True)
            (source_dir / "artifact.txt").write_text(f"{key}\n", encoding="utf-8")
            summary[key] = str(source_dir)

        original_copytree = shutil.copytree
        collision_triggered = {"value": False}

        def copytree_with_collision(src: str | Path, dst: str | Path, *args: object, **kwargs: object) -> str:
            if not collision_triggered["value"]:
                Path(dst).mkdir(parents=True, exist_ok=False)
                collision_triggered["value"] = True
                raise FileExistsError(dst)
            return original_copytree(src, dst, *args, **kwargs)

        with mock.patch("scripts.rebuild_sample_stack.shutil.copytree", side_effect=copytree_with_collision):
            compat_report = rebuild_sample_stack.export_latest_tmp_compat(summary, retain=2, prune=False, tmp_root=tmp_root)

        exports = compat_report["exports"]
        self.assertEqual(exports["version"], "2")
        self.assertTrue((tmp_root / "working-clone-bundle-v1").exists())
        self.assertTrue((tmp_root / "working-clone-bundle-v2").exists())
        self.assertTrue(collision_triggered["value"])

    def test_rebuild_sample_stack_and_doctor_commands(self) -> None:
        output_root = self.root / "sample-stack"
        rebuild = self.run_cmd("scripts/rebuild_sample_stack.py", "--output-root", str(output_root))
        self.assertEqual(rebuild.returncode, 0, rebuild.stderr)
        rebuild_report = json.loads(rebuild.stdout)

        sample_summary = output_root / "SAMPLE_STACK_SUMMARY.json"
        self.assertTrue(sample_summary.exists())
        sample_summary_payload = json.loads(sample_summary.read_text(encoding="utf-8"))

        clone_config = output_root / "working-clone-bundle" / "personal-clone-skill" / "clone_config.yaml"
        self.assertIn(rebuild_sample_stack.DEFAULT_SAMPLE_TIMESTAMP, clone_config.read_text(encoding="utf-8"))

        second_rebuild = self.run_cmd(
            "scripts/rebuild_sample_stack.py",
            "--output-root",
            str(output_root),
            "--skip-export-latest-tmp",
        )
        self.assertEqual(second_rebuild.returncode, 0, second_rebuild.stderr)
        second_sample_summary = json.loads(sample_summary.read_text(encoding="utf-8"))
        self.assertEqual(sample_summary_payload["signatures"], second_sample_summary["signatures"])

        latest_tmp_exports = rebuild_report.get("latest_tmp_exports", {})
        exported_bundle = Path(str(latest_tmp_exports.get("bundle_dir", "")))
        exported_pipeline = Path(str(latest_tmp_exports.get("pipeline_dir", "")))
        exported_runtime = Path(str(latest_tmp_exports.get("runtime_dir", "")))
        exported_personal = Path(str(latest_tmp_exports.get("personal_skill_dir", "")))
        exported_workflow = Path(str(latest_tmp_exports.get("workflow_skill_dir", "")))
        self.assertTrue(exported_bundle.exists())
        self.assertTrue(exported_pipeline.exists())
        self.assertTrue(exported_runtime.exists())
        self.assertTrue(exported_personal.exists())
        self.assertTrue(exported_workflow.exists())

        bundle_manifest = json.loads((exported_bundle / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        pipeline_manifest = json.loads((exported_pipeline / "workflow_blueprint_pipeline_manifest.json").read_text(encoding="utf-8"))
        runtime_manifest = json.loads((exported_runtime / "workflow_runtime_manifest.json").read_text(encoding="utf-8"))
        personal_manifest = json.loads((exported_personal / "personal_clone_skill_manifest.json").read_text(encoding="utf-8"))
        bundle_readme = (exported_bundle / "WORKING_CLONE_BUNDLE_README.md").read_text(encoding="utf-8")
        pipeline_readme = (exported_pipeline / "WORKFLOW_BLUEPRINT_PIPELINE_README.md").read_text(encoding="utf-8")
        runtime_readme = (exported_runtime / "WORKFLOW_RUNTIME_README.md").read_text(encoding="utf-8")
        workflow_blueprint = (output_root / "working-clone-bundle" / "workflow-blueprint-pipeline" / "workflow_blueprint.md").read_text(
            encoding="utf-8"
        )
        runtime_skill = (
            output_root
            / "working-clone-bundle"
            / "workflow-blueprint-pipeline"
            / "workflow-runtime-bundle"
            / "workflow-clone-runtime"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(bundle_manifest["workflow_blueprint"], str(exported_pipeline / "workflow_blueprint.md"))
        self.assertEqual(bundle_manifest["workflow_clone_skill"], str(exported_workflow))
        self.assertTrue(bundle_manifest["steps"]["workflow_clone_skill"])
        self.assertEqual(pipeline_manifest["clone_config"], str(exported_personal / "clone_config.yaml"))
        self.assertEqual(pipeline_manifest["blueprint"], str(exported_pipeline / "workflow_blueprint.md"))
        self.assertEqual(runtime_manifest["clone_config"], str(exported_personal / "clone_config.yaml"))
        self.assertEqual(runtime_manifest["workflow_blueprint"], str(exported_pipeline / "workflow_blueprint.md"))
        self.assertEqual(
            personal_manifest["source_artifacts"]["clone_config"]["path"],
            str(exported_bundle / "personal-clone-skill.yaml"),
        )
        self.assertTrue(Path(personal_manifest["source_artifacts"]["clone_config"]["path"]).exists())
        self.assertNotIn(str(output_root), bundle_readme)
        self.assertIn("## User View", bundle_readme)
        self.assertIn("## Operator View", bundle_readme)
        self.assertIn("## User View", pipeline_readme)
        self.assertIn("## Operator View", pipeline_readme)
        self.assertIn("## User View", runtime_readme)
        self.assertIn("## Operator View", runtime_readme)
        self.assertIn("workflow_clone_skill_ready: true", bundle_readme)
        self.assertIn("workflow_usage_now: workflow runtime 已就绪，可以继续跑任务回合。", bundle_readme)
        self.assertIn(f"workflow_clone_skill: {exported_workflow}", bundle_readme)
        self.assertIn("### 1. 接收需求", workflow_blueprint)
        self.assertIn("### 2. 澄清验收标准", workflow_blueprint)
        self.assertIn("### 3. 拆解技术路径", workflow_blueprint)
        self.assertNotIn("### 1. 阶段1", workflow_blueprint)
        self.assertNotIn("暂无阶段动作", workflow_blueprint)
        self.assertNotIn("暂无工具映射", workflow_blueprint)
        self.assertNotIn("暂无阶段切换规则", workflow_blueprint)
        self.assertNotIn("暂无人工介入点", workflow_blueprint)
        self.assertNotIn("暂无阶段定义", runtime_skill)

        exported_validate = self.run_cmd(
            "scripts/validate_clone_stack.py",
            "--bundle-manifest",
            str(exported_bundle / "working_clone_bundle_manifest.json"),
            "--bundle-summary",
            str(exported_bundle / "working_clone_until_final_summary.json"),
            "--bundle-readme",
            str(exported_bundle / "WORKING_CLONE_BUNDLE_README.md"),
            "--pipeline-manifest",
            str(exported_pipeline / "workflow_blueprint_pipeline_manifest.json"),
            "--pipeline-readme",
            str(exported_pipeline / "WORKFLOW_BLUEPRINT_PIPELINE_README.md"),
            "--runtime-manifest",
            str(exported_runtime / "workflow_runtime_manifest.json"),
            "--runtime-readme",
            str(exported_runtime / "WORKFLOW_RUNTIME_README.md"),
            "--personal-skill-dir",
            str(exported_personal),
            "--workflow-skill-dir",
            str(exported_workflow),
            "--format",
            "json",
        )
        self.assertEqual(exported_validate.returncode, 0, exported_validate.stderr)

        sample_doctor_summary = self.root / "doctor-sample-summary.json"
        doctor_sample = self.run_cmd(
            "scripts/clone_ops.py",
            "doctor",
            "sample-stack",
            "--sample-summary",
            str(sample_summary),
            "--summary-json",
            str(sample_doctor_summary),
        )
        self.assertEqual(doctor_sample.returncode, 0, doctor_sample.stderr)
        self.assertTrue(sample_doctor_summary.exists())

        bundle_dir = output_root / "working-clone-bundle"
        current_summary = self.root / "current-stack-summary.json"
        current_doctor = self.run_cmd(
            "scripts/clone_ops.py",
            "doctor",
            "current-stack",
            "--bundle-dir",
            str(bundle_dir),
            "--summary-json",
            str(current_summary),
        )
        self.assertEqual(current_doctor.returncode, 0, current_doctor.stderr)
        self.assertTrue(current_summary.exists())

        latest_summary = self.root / "latest-stack-summary.json"
        latest_doctor = self.run_cmd(
            "scripts/clone_ops.py",
            "doctor",
            "latest-stack",
            "--summary-json",
            str(latest_summary),
        )
        self.assertEqual(latest_doctor.returncode, 0, latest_doctor.stderr)
        self.assertTrue(latest_summary.exists())
        latest_summary_payload = json.loads(latest_summary.read_text(encoding="utf-8"))
        self.assertEqual(latest_summary_payload["selection_mode"], "latest_coherent_stack")
        self.assertTrue(Path(latest_summary_payload["bundle_dir"]).exists())
        self.assertTrue(Path(latest_summary_payload["pipeline_dir"]).exists())
        self.assertTrue(Path(latest_summary_payload["runtime_dir"]).exists())
        self.assertTrue(Path(latest_summary_payload["personal_skill_dir"]).exists())
        self.assertTrue(Path(latest_summary_payload["workflow_skill_dir"]).exists())

        latest_validate = self.run_cmd(
            "scripts/clone_ops.py",
            "validate",
            "latest-stack",
            "--summary-json",
            str(self.root / "latest-stack-validate-summary.json"),
        )
        self.assertEqual(latest_validate.returncode, 0, latest_validate.stderr)

        latest_explain = self.run_cmd(
            "scripts/clone_ops.py",
            "explain",
            "latest-stack",
            "--summary-json",
            str(self.root / "latest-stack-explain-summary.json"),
        )
        self.assertEqual(latest_explain.returncode, 0, latest_explain.stderr)
        self.assertIn("selection_mode:", latest_explain.stdout)
        self.assertIn("bundle_refresh: watch_groups=bundle_core,workflow_shared", latest_explain.stdout)
        self.assertIn("pipeline_refresh: watch_groups=workflow_shared", latest_explain.stdout)
        self.assertIn("runtime_refresh: watch_groups=workflow_shared,runtime_core", latest_explain.stdout)

        diff_proc = self.run_cmd(
            "scripts/clone_ops.py",
            "diff",
            "stack",
            "--left-summary",
            str(sample_summary),
            "--right-summary",
            str(current_summary),
        )
        self.assertEqual(diff_proc.returncode, 0, diff_proc.stdout + diff_proc.stderr)
        diff_report = json.loads(diff_proc.stdout)
        self.assertTrue(diff_report["ok"])

    def test_refresh_scripts_and_release_readiness(self) -> None:
        bundle_dir = self.root / "custom-working-clone-bundle"
        copied = self.build_custom_working_bundle(bundle_dir)

        working_marker = "\n- refresh-marker-working\n"
        copied["mind_profile.md"].write_text(
            copied["mind_profile.md"].read_text(encoding="utf-8") + working_marker,
            encoding="utf-8",
        )
        refresh_working = self.run_cmd(
            "scripts/refresh_working_clone_bundle.py",
            "--manifest",
            str(bundle_dir / "working_clone_bundle_manifest.json"),
        )
        self.assertEqual(refresh_working.returncode, 0, refresh_working.stderr)
        self.assertIn(working_marker.strip(), (bundle_dir / "personal-clone-skill" / "mind_profile.md").read_text(encoding="utf-8"))

        pipeline_marker = "交付与回归检查"
        copied["workflow_interview_filled.md"].write_text(
            copied["workflow_interview_filled.md"].read_text(encoding="utf-8").replace("交付与复盘", pipeline_marker),
            encoding="utf-8",
        )
        refresh_pipeline = self.run_cmd(
            "scripts/refresh_workflow_blueprint_pipeline.py",
            "--manifest",
            str(bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json"),
        )
        self.assertEqual(refresh_pipeline.returncode, 0, refresh_pipeline.stderr)
        pipeline_blueprint = bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint.md"
        self.assertIn(pipeline_marker, pipeline_blueprint.read_text(encoding="utf-8"))

        runtime_marker = "交付与发布收尾"
        pipeline_blueprint.write_text(
            pipeline_blueprint.read_text(encoding="utf-8").replace(pipeline_marker, runtime_marker),
            encoding="utf-8",
        )
        refresh_runtime = self.run_cmd(
            "scripts/refresh_workflow_runtime_bundle.py",
            "--manifest",
            str(
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ),
        )
        self.assertEqual(refresh_runtime.returncode, 0, refresh_runtime.stderr)
        runtime_skill_blueprint = (
            bundle_dir
            / "workflow-blueprint-pipeline"
            / "workflow-runtime-bundle"
            / "workflow-clone-runtime"
            / "workflow_blueprint.md"
        )
        self.assertIn(runtime_marker, runtime_skill_blueprint.read_text(encoding="utf-8"))

        working_template_marker = "TEMPLATE_REFRESH_MARKER_WORKING"
        pipeline_template_marker = "TEMPLATE_REFRESH_MARKER_PIPELINE"
        runtime_template_marker = "TEMPLATE_REFRESH_MARKER_RUNTIME"
        working_template = REPO_ROOT / "templates" / "working_clone_bundle_readme_template.md"
        pipeline_template = REPO_ROOT / "templates" / "workflow_blueprint_pipeline_readme_template.md"
        runtime_template = REPO_ROOT / "templates" / "workflow_runtime_readme_template.md"

        self.patch_repo_file(working_template, working_template_marker)
        refresh_working_from_template = self.run_cmd(
            "scripts/refresh_working_clone_bundle.py",
            "--manifest",
            str(bundle_dir / "working_clone_bundle_manifest.json"),
        )
        self.assertEqual(refresh_working_from_template.returncode, 0, refresh_working_from_template.stderr)
        self.assertIn(
            working_template_marker,
            (bundle_dir / "WORKING_CLONE_BUNDLE_README.md").read_text(encoding="utf-8"),
        )
        working_manifest_after_template = json.loads((bundle_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            working_manifest_after_template["last_refresh_trigger"]["changed_groups"],
            ["bundle_core"],
        )
        self.assertEqual(
            working_manifest_after_template["last_refresh_trigger"]["changed_classes"],
            ["content_changed"],
        )
        self.assertGreaterEqual(len(working_manifest_after_template.get("refresh_trigger_history", [])), 2)
        self.assertEqual(
            working_manifest_after_template["refresh_trigger_history"][-1]["changed_classes"],
            ["content_changed"],
        )
        self.assertTrue(
            any(
                item["name"] == "working_clone_bundle_readme_template.md"
                for item in working_manifest_after_template["last_refresh_trigger"]["changed_files"]
            )
        )

        self.patch_repo_file(pipeline_template, pipeline_template_marker)
        refresh_pipeline_from_template = self.run_cmd(
            "scripts/refresh_workflow_blueprint_pipeline.py",
            "--manifest",
            str(bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json"),
        )
        self.assertEqual(refresh_pipeline_from_template.returncode, 0, refresh_pipeline_from_template.stderr)
        self.assertIn(
            pipeline_template_marker,
            (bundle_dir / "workflow-blueprint-pipeline" / "WORKFLOW_BLUEPRINT_PIPELINE_README.md").read_text(encoding="utf-8"),
        )
        pipeline_manifest_after_template = json.loads(
            (bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            pipeline_manifest_after_template["last_refresh_trigger"]["changed_groups"],
            ["workflow_shared"],
        )
        self.assertEqual(
            pipeline_manifest_after_template["last_refresh_trigger"]["changed_classes"],
            ["content_changed"],
        )
        self.assertGreaterEqual(len(pipeline_manifest_after_template.get("refresh_trigger_history", [])), 1)
        self.assertTrue(
            any(
                item["name"] == "workflow_blueprint_pipeline_readme_template.md"
                for item in pipeline_manifest_after_template["last_refresh_trigger"]["changed_files"]
            )
        )

        self.patch_repo_file(runtime_template, runtime_template_marker)
        refresh_runtime_from_template = self.run_cmd(
            "scripts/refresh_workflow_runtime_bundle.py",
            "--manifest",
            str(
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ),
        )
        self.assertEqual(refresh_runtime_from_template.returncode, 0, refresh_runtime_from_template.stderr)
        self.assertIn(
            runtime_template_marker,
            (bundle_dir / "workflow-blueprint-pipeline" / "workflow-runtime-bundle" / "WORKFLOW_RUNTIME_README.md").read_text(encoding="utf-8"),
        )
        runtime_manifest_after_template = json.loads(
            (
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            runtime_manifest_after_template["last_refresh_trigger"]["changed_groups"],
            ["workflow_shared"],
        )
        self.assertEqual(
            runtime_manifest_after_template["last_refresh_trigger"]["changed_classes"],
            ["content_changed"],
        )
        self.assertGreaterEqual(len(runtime_manifest_after_template.get("refresh_trigger_history", [])), 1)
        self.assertTrue(
            any(
                item["name"] == "workflow_runtime_readme_template.md"
                for item in runtime_manifest_after_template["last_refresh_trigger"]["changed_files"]
            )
        )

        working_script = REPO_ROOT / "scripts" / "build_personal_clone_skill.py"
        pipeline_script = REPO_ROOT / "scripts" / "build_workflow_blueprint.py"
        runtime_script = REPO_ROOT / "scripts" / "bootstrap_workflow_clone_runtime.py"

        working_manifest_before = json.loads((bundle_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        self.patch_repo_file(working_script, "# SCRIPT_REFRESH_MARKER_WORKING")
        refresh_working_from_script = self.run_cmd(
            "scripts/refresh_working_clone_bundle.py",
            "--manifest",
            str(bundle_dir / "working_clone_bundle_manifest.json"),
        )
        self.assertEqual(refresh_working_from_script.returncode, 0, refresh_working_from_script.stderr)
        working_manifest_after = json.loads((bundle_dir / "working_clone_bundle_manifest.json").read_text(encoding="utf-8"))
        self.assertNotEqual(
            working_manifest_before["refresh_cache"]["fingerprint"],
            working_manifest_after["refresh_cache"]["fingerprint"],
        )
        self.assertIn("bundle_core", working_manifest_after["last_refresh_trigger"]["changed_groups"])
        self.assertIn("content_changed", working_manifest_after["last_refresh_trigger"]["changed_classes"])
        self.assertLessEqual(len(working_manifest_after.get("refresh_trigger_history", [])), 5)
        self.assertEqual(
            working_manifest_after["refresh_trigger_history"][-1]["changed_files"][0]["name"],
            "build_personal_clone_skill.py",
        )
        self.assertTrue(
            any(item["name"] == "build_personal_clone_skill.py" for item in working_manifest_after["last_refresh_trigger"]["changed_files"])
        )
        pipeline_manifest_after_bundle_refresh = json.loads(
            (bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            pipeline_manifest_after_bundle_refresh["last_refresh_trigger"]["reason"],
            "propagated_from_bundle_refresh",
        )
        self.assertEqual(
            pipeline_manifest_after_bundle_refresh["last_refresh_trigger"]["changed_groups"],
            ["workflow_shared"],
        )
        self.assertTrue(
            any(
                item["name"] == "workflow_blueprint_pipeline_readme_template.md"
                for item in pipeline_manifest_after_bundle_refresh["last_refresh_trigger"]["changed_files"]
            )
        )
        runtime_manifest_after_bundle_refresh = json.loads(
            (
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            runtime_manifest_after_bundle_refresh["last_refresh_trigger"]["reason"],
            "propagated_from_bundle_refresh",
        )
        self.assertEqual(
            runtime_manifest_after_bundle_refresh["last_refresh_trigger"]["changed_groups"],
            ["workflow_shared"],
        )
        self.assertTrue(
            any(
                item["name"] == "workflow_runtime_readme_template.md"
                for item in runtime_manifest_after_bundle_refresh["last_refresh_trigger"]["changed_files"]
            )
        )

        pipeline_manifest_before = json.loads(
            (bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json").read_text(encoding="utf-8")
        )
        self.patch_repo_file(pipeline_script, "# SCRIPT_REFRESH_MARKER_PIPELINE")
        refresh_pipeline_from_script = self.run_cmd(
            "scripts/refresh_workflow_blueprint_pipeline.py",
            "--manifest",
            str(bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json"),
        )
        self.assertEqual(refresh_pipeline_from_script.returncode, 0, refresh_pipeline_from_script.stderr)
        pipeline_manifest_after = json.loads(
            (bundle_dir / "workflow-blueprint-pipeline" / "workflow_blueprint_pipeline_manifest.json").read_text(encoding="utf-8")
        )
        self.assertNotEqual(
            pipeline_manifest_before["refresh_cache"]["fingerprint"],
            pipeline_manifest_after["refresh_cache"]["fingerprint"],
        )
        self.assertIn("workflow_shared", pipeline_manifest_after["last_refresh_trigger"]["changed_groups"])
        self.assertIn("content_changed", pipeline_manifest_after["last_refresh_trigger"]["changed_classes"])
        self.assertLessEqual(len(pipeline_manifest_after.get("refresh_trigger_history", [])), 5)
        self.assertEqual(
            pipeline_manifest_after["refresh_trigger_history"][-1]["changed_files"][0]["name"],
            "build_workflow_blueprint.py",
        )
        self.assertTrue(
            any(item["name"] == "build_workflow_blueprint.py" for item in pipeline_manifest_after["last_refresh_trigger"]["changed_files"])
        )

        runtime_manifest_before = json.loads(
            (
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.patch_repo_file(runtime_script, "# SCRIPT_REFRESH_MARKER_RUNTIME")
        refresh_runtime_from_script = self.run_cmd(
            "scripts/refresh_workflow_runtime_bundle.py",
            "--manifest",
            str(
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ),
        )
        self.assertEqual(refresh_runtime_from_script.returncode, 0, refresh_runtime_from_script.stderr)
        runtime_manifest_after = json.loads(
            (
                bundle_dir
                / "workflow-blueprint-pipeline"
                / "workflow-runtime-bundle"
                / "workflow_runtime_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertNotEqual(
            runtime_manifest_before["refresh_cache"]["fingerprint"],
            runtime_manifest_after["refresh_cache"]["fingerprint"],
        )
        self.assertIn("workflow_shared", runtime_manifest_after["last_refresh_trigger"]["changed_groups"])
        self.assertIn("content_changed", runtime_manifest_after["last_refresh_trigger"]["changed_classes"])
        self.assertLessEqual(len(runtime_manifest_after.get("refresh_trigger_history", [])), 5)
        self.assertEqual(
            runtime_manifest_after["refresh_trigger_history"][-1]["changed_files"][0]["name"],
            "bootstrap_workflow_clone_runtime.py",
        )
        self.assertTrue(
            any(item["name"] == "bootstrap_workflow_clone_runtime.py" for item in runtime_manifest_after["last_refresh_trigger"]["changed_files"])
        )

        explain_current = self.run_cmd(
            "scripts/clone_ops.py",
            "doctor",
            "current-stack",
            "--bundle-dir",
            str(bundle_dir),
            "--explain",
            "--summary-json",
            str(self.root / "current-stack-refresh-explain.json"),
        )
        self.assertEqual(explain_current.returncode, 0, explain_current.stderr)
        self.assertIn("bundle_refresh: watch_groups=bundle_core,workflow_shared", explain_current.stderr)
        self.assertIn("last=", explain_current.stderr)
        self.assertIn("build_personal_clone_skill.py", explain_current.stderr)
        self.assertIn("[content_changed]", explain_current.stderr)
        self.assertIn("last_groups=bundle_core,workflow_shared", explain_current.stderr)
        self.assertIn("pipeline_refresh: watch_groups=workflow_shared", explain_current.stderr)
        self.assertIn("build_workflow_blueprint.py[content_changed]", explain_current.stderr)
        self.assertIn("runtime_refresh: watch_groups=workflow_shared,runtime_core", explain_current.stderr)
        self.assertIn("bootstrap_workflow_clone_runtime.py[content_changed]", explain_current.stderr)
        self.assertIn("stats=history=", explain_current.stderr)
        self.assertIn("top_groups=bundle_core:2", explain_current.stderr)
        self.assertIn("top_classes=content_changed:3", explain_current.stderr)
        self.assertIn("top_groups=workflow_shared:3", explain_current.stderr)
        self.assertIn("top_classes=content_changed:4", explain_current.stderr)
        self.assertIn("build_workflow_blueprint.py:1", explain_current.stderr)
        self.assertIn("workflow_blueprint_pipeline_readme_template.md:2", explain_current.stderr)
        self.assertIn("top_groups=workflow_shared:5", explain_current.stderr)
        self.assertIn("top_classes=content_changed:5", explain_current.stderr)
        self.assertIn("bootstrap_workflow_clone_runtime.py:1", explain_current.stderr)
        self.assertIn("workflow_runtime_readme_template.md:2", explain_current.stderr)

        release_root = self.root / "release-ready-stack"
        release_summary = self.root / "release-readiness-summary.json"
        release_check = self.run_cmd(
            "scripts/clone_ops.py",
            "validate",
            "release-readiness",
            "--output-root",
            str(release_root),
            "--skip-tests",
            "--summary-json",
            str(release_summary),
        )
        self.assertEqual(release_check.returncode, 0, release_check.stderr)
        release_report = json.loads(release_summary.read_text(encoding="utf-8"))
        self.assertTrue(release_report["ok"])
        self.assertFalse((release_root / "release-logs").exists())
        self.assertEqual(
            [step["label"] for step in release_report["steps"]],
            [
                "validate_repo_docs",
                "rebuild_sample_stack",
                "validate_sample_workflow_blueprint",
                "doctor_sample_stack",
                "doctor_current_stack",
                "doctor_latest_stack",
                "validate_latest_stack",
                "explain_latest_stack",
            ],
        )
        step_map = {step["label"]: step for step in release_report["steps"]}
        self.assertEqual(step_map["validate_repo_docs"]["compact_summary"]["headline"], "repo docs validation passed")
        self.assertTrue(
            any(
                "issues: missing_docs=0" in detail
                for detail in step_map["validate_repo_docs"]["compact_summary"]["details"]
            )
        )
        self.assertIn("compact_summary", step_map["rebuild_sample_stack"])
        self.assertFalse(
            any(detail.startswith("signatures:") for detail in step_map["rebuild_sample_stack"]["compact_summary"]["details"])
        )
        self.assertFalse(any(detail.startswith("bundle:") for detail in step_map["rebuild_sample_stack"]["compact_summary"]["details"]))
        self.assertEqual(
            step_map["validate_sample_workflow_blueprint"]["compact_summary"]["headline"],
            "workflow blueprint gate passed",
        )
        self.assertIn(
            "stack_ref: sample_stack_summary | bundle=working-clone-bundle | pipeline=workflow-blueprint-pipeline | runtime=workflow-runtime-bundle",
            step_map["doctor_sample_stack"]["compact_summary"]["details"],
        )
        self.assertFalse(
            any(detail.startswith("signatures:") for detail in step_map["doctor_sample_stack"]["compact_summary"]["details"])
        )
        self.assertIn(
            "stack_ref: bundle_anchored_stack | bundle=working-clone-bundle | pipeline=workflow-blueprint-pipeline | runtime=workflow-runtime-bundle",
            step_map["doctor_current_stack"]["compact_summary"]["details"],
        )
        self.assertFalse(
            any(detail.startswith("signatures:") for detail in step_map["doctor_current_stack"]["compact_summary"]["details"])
        )
        self.assertIn(
            "stack_ref: latest_coherent_stack | bundle=working-clone-bundle-v",
            "\n".join(step_map["doctor_latest_stack"]["compact_summary"]["details"]),
        )
        self.assertFalse(
            any(detail.startswith("signatures:") for detail in step_map["doctor_latest_stack"]["compact_summary"]["details"])
        )
        self.assertIn(
            "stack_ref: latest_coherent_stack | bundle=working-clone-bundle-v",
            "\n".join(step_map["validate_latest_stack"]["compact_summary"]["details"]),
        )
        self.assertFalse(
            any(detail.startswith("signatures:") for detail in step_map["validate_latest_stack"]["compact_summary"]["details"])
        )
        self.assertIn(
            "stack_ref: latest_coherent_stack | bundle=working-clone-bundle-v",
            "\n".join(step_map["explain_latest_stack"]["compact_summary"]["details"]),
        )
        self.assertTrue(
            any(detail.startswith("signatures:") for detail in step_map["explain_latest_stack"]["compact_summary"]["details"])
        )
        self.assertTrue(
            any(detail.startswith("refresh_hotspots:") for detail in step_map["explain_latest_stack"]["compact_summary"]["details"])
        )
        latest_stack_refs = [
            next(
                detail
                for detail in step_map[label]["compact_summary"]["details"]
                if detail.startswith("stack_ref:")
            )
            for label in ["doctor_latest_stack", "validate_latest_stack", "explain_latest_stack"]
        ]
        self.assertEqual(latest_stack_refs[0], latest_stack_refs[1])
        self.assertEqual(latest_stack_refs[1], latest_stack_refs[2])
        self.assertNotIn("validation: 9/9 passed", step_map["doctor_latest_stack"]["compact_summary"]["details"])
        self.assertFalse(
            any(detail.startswith("skills:") for detail in step_map["doctor_latest_stack"]["compact_summary"]["details"])
        )
        for step in release_report["steps"]:
            self.assertNotIn("stdout", step)
            self.assertNotIn("stderr", step)
            self.assertIn("compact_summary", step)
            self.assertTrue(step["compact_summary"]["headline"])
            self.assertIsInstance(step["compact_summary"]["details"], list)
            self.assertEqual(step.get("stdout_preview", ""), "")
            self.assertEqual(step.get("stderr_preview", ""), "")
            self.assertEqual(step.get("stdout_log_path", ""), "")
            self.assertEqual(step.get("stderr_log_path", ""), "")
            if step.get("summary_json_path"):
                self.assertTrue(Path(step["summary_json_path"]).exists())


if __name__ == "__main__":
    unittest.main()
