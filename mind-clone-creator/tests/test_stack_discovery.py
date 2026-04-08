from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import manifest_utils
from scripts import refresh_dependency_registry
from scripts import stack_discovery


class StackDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="mind-clone-tests-")
        self.root = Path(self.tempdir.name)
        self.workdir = self.root

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_collect_valid_tmp_dirs_prefers_only_complete_candidates(self) -> None:
        prefix = f"mind-clone-test-{next(tempfile._get_candidate_names())}-v"
        invalid = Path("/tmp") / f"{prefix}1"
        valid = Path("/tmp") / f"{prefix}2"
        invalid.mkdir(parents=True, exist_ok=True)
        valid.mkdir(parents=True, exist_ok=True)
        try:
            (invalid / "required.txt").write_text("missing second\n", encoding="utf-8")
            (valid / "required.txt").write_text("ok\n", encoding="utf-8")
            (valid / "second.txt").write_text("ok\n", encoding="utf-8")
            paths = stack_discovery.collect_valid_tmp_dirs(
                prefix,
                ["required.txt", "second.txt"],
                None,
                self.workdir,
            )
            self.assertEqual(paths[0], valid)
        finally:
            for path in [invalid, valid]:
                for child in path.glob("*"):
                    child.unlink()
                path.rmdir()

    def test_select_latest_coherent_stack_matches_by_content_signature(self) -> None:
        bundle = self._make_bundle(self.root / "bundle-v2", clone_value="A", blueprint_value="B")
        pipeline_old = self._make_pipeline(self.root / "pipeline-v9", clone_value="A", blueprint_value="OLD")
        pipeline_new = self._make_pipeline(self.root / "pipeline-v3", clone_value="A", blueprint_value="B")
        runtime = self._make_runtime(self.root / "runtime-v4", clone_value="A", blueprint_value="B")
        personal = self._make_personal_skill(self.root / "personal-v7", clone_value="A")
        workflow = self._make_workflow_skill(self.root / "workflow-v5", clone_value="A", blueprint_value="B")

        with mock.patch.object(stack_discovery, "run_validation", return_value=True):
            selected = stack_discovery.select_latest_coherent_stack(
                self.workdir,
                [bundle],
                [pipeline_old, pipeline_new],
                [runtime],
                [personal],
                [workflow],
            )

        self.assertEqual(selected[1], pipeline_new)
        summary = stack_discovery.build_stack_summary(*selected)
        self.assertEqual(summary["signatures"]["bundle"]["workflow_blueprint_hash"], summary["signatures"]["pipeline"]["workflow_blueprint_hash"])

    def test_select_latest_coherent_stack_prefers_version_aligned_matches_over_newer_mixed_artifacts(self) -> None:
        bundle = self._make_bundle(self.root / "bundle-v129", clone_value="A", blueprint_value="B")
        pipeline_aligned = self._make_pipeline(self.root / "pipeline-v129", clone_value="A", blueprint_value="B")
        pipeline_newer = self._make_pipeline(self.root / "pipeline-v130", clone_value="A", blueprint_value="B")
        runtime_aligned = self._make_runtime(self.root / "runtime-v129", clone_value="A", blueprint_value="B")
        runtime_newer = self._make_runtime(self.root / "runtime-v130", clone_value="A", blueprint_value="B")
        personal_aligned = self._make_personal_skill(self.root / "personal-v129", clone_value="A")
        personal_newer = self._make_personal_skill(self.root / "personal-v130", clone_value="A")
        workflow_aligned = self._make_workflow_skill(self.root / "workflow-v129", clone_value="A", blueprint_value="B")
        workflow_newer = self._make_workflow_skill(self.root / "workflow-v130", clone_value="A", blueprint_value="B")

        with mock.patch.object(stack_discovery, "run_validation", return_value=True):
            selected, report = stack_discovery.select_latest_coherent_stack_with_report(
                self.workdir,
                [bundle],
                [pipeline_newer, pipeline_aligned],
                [runtime_newer, runtime_aligned],
                [personal_newer, personal_aligned],
                [workflow_newer, workflow_aligned],
            )

        self.assertEqual(selected[0], bundle)
        self.assertEqual(selected[1], pipeline_aligned)
        self.assertEqual(selected[2], runtime_aligned)
        self.assertEqual(selected[3], personal_aligned)
        self.assertEqual(selected[4], workflow_aligned)
        self.assertEqual(report["cohort_alignment"]["target_version"], 129)

    def test_select_latest_coherent_stack_prefers_older_bundle_when_it_completes_the_best_aligned_signature_group(self) -> None:
        bundle_newer = self._make_bundle(self.root / "bundle-v130", clone_value="A", blueprint_value="B")
        bundle_aligned = self._make_bundle(self.root / "bundle-v129", clone_value="A", blueprint_value="B")
        pipeline = self._make_pipeline(self.root / "pipeline-v129", clone_value="A", blueprint_value="B")
        runtime = self._make_runtime(self.root / "runtime-v129", clone_value="A", blueprint_value="B")
        personal = self._make_personal_skill(self.root / "personal-v129", clone_value="A")
        workflow = self._make_workflow_skill(self.root / "workflow-v129", clone_value="A", blueprint_value="B")

        with mock.patch.object(stack_discovery, "run_validation", return_value=True):
            selected, report = stack_discovery.select_latest_coherent_stack_with_report(
                self.workdir,
                [bundle_newer, bundle_aligned],
                [pipeline],
                [runtime],
                [personal],
                [workflow],
            )

        self.assertEqual(selected[0], bundle_aligned)
        self.assertEqual(selected[1], pipeline)
        self.assertEqual(selected[2], runtime)
        self.assertEqual(selected[3], personal)
        self.assertEqual(selected[4], workflow)
        self.assertEqual(report["selected_bundle"], str(bundle_aligned))
        self.assertEqual(report["cohort_alignment"]["target_version"], 129)

    def test_build_freshness_report_treats_aligned_selection_as_note_not_warning(self) -> None:
        pipeline_aligned = self._make_pipeline(self.root / "pipeline-v129", clone_value="A", blueprint_value="B")
        pipeline_newer = self._make_pipeline(self.root / "pipeline-v130", clone_value="A", blueprint_value="B")
        report_129 = stack_discovery.describe_candidate_path(pipeline_aligned) | {"status": "valid", "reason": "ok"}
        report_130 = stack_discovery.describe_candidate_path(pipeline_newer) | {"status": "valid", "reason": "ok"}

        freshness = stack_discovery.build_freshness_report(
            {"pipeline": pipeline_aligned},
            {"pipeline": [report_130, report_129]},
            group_candidates={"pipeline": [pipeline_newer, pipeline_aligned]},
            cohort_alignment={"target_version": 129, "versions": {"pipeline": 129}},
        )

        self.assertEqual(freshness["warnings"], [])
        self.assertEqual(len(freshness["notes"]), 1)
        self.assertIn("align with cohort target v129", freshness["notes"][0])
        self.assertEqual(freshness["categories"]["pipeline"]["freshness_status"], "aligned_selection")
        self.assertEqual(freshness["categories"]["pipeline"]["newer_matching_candidate_count"], 1)

    def test_render_stack_summary_text_groups_freshness_notes_and_warnings(self) -> None:
        rendered = stack_discovery.render_stack_summary_text(
            {
                "selection_mode": "latest_coherent_stack",
                "bundle_dir": "/tmp/working-clone-bundle-v129",
                "pipeline_dir": "/tmp/workflow-blueprint-pipeline-v129",
                "runtime_dir": "/tmp/workflow-runtime-v129",
                "personal_skill_dir": "/tmp/personal-clone-skill-v129",
                "workflow_skill_dir": "/tmp/workflow-clone-skill-v129",
                "refresh_watch": {
                    "bundle": {
                        "groups": ["bundle_core", "workflow_shared"],
                        "tracked_files_count": 36,
                    }
                },
                "last_refresh_trigger": {
                    "bundle": {
                        "changed_groups": ["bundle_core", "workflow_shared"],
                        "changed_classes": ["content_changed"],
                        "changed_files": [{"name": "build_personal_clone_skill.py"}],
                    }
                },
                "refresh_trigger_history": {
                    "bundle": [
                        {
                            "changed_classes": ["content_changed"],
                            "changed_files": [{"name": "build_personal_clone_skill.py"}],
                        }
                    ]
                },
                "refresh_stats": {
                    "bundle": {
                        "history_count": 1,
                        "top_files": [{"value": "build_personal_clone_skill.py", "count": 1}],
                        "top_groups": [{"value": "bundle_core", "count": 1}],
                        "top_classes": [{"value": "content_changed", "count": 1}],
                    }
                },
                "discovery_report": {
                    "cohort_alignment": {
                        "target_version": 129,
                    },
                    "rejection_counts": {
                        "bundle": 0,
                        "pipeline": 2,
                        "runtime": 1,
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
                    "freshness": {
                        "categories": {
                            "pipeline": {"freshness_status": "aligned_selection"},
                            "runtime": {"freshness_status": "stale_same_signature"},
                            "workflow_skill": {"freshness_status": "newer_other_signatures"},
                        },
                        "warnings": ["runtime warning"],
                        "notes": ["pipeline note", "workflow note"],
                    },
                },
            }
        )

        self.assertIn("freshness_warnings: same_signature_newer=runtime", rendered)
        self.assertIn("freshness_notes: other_signature_newer=workflow; aligned_to_v129=pipeline", rendered)
        self.assertIn("candidate_rejections: pipeline=2, runtime=1", rendered)
        self.assertIn(
            "bundle_refresh: watch_groups=bundle_core,workflow_shared tracked_files=36 last=build_personal_clone_skill.py[content_changed] last_groups=bundle_core,workflow_shared recent=build_personal_clone_skill.py[content_changed] stats=history=1 top_files=build_personal_clone_skill.py:1 top_groups=bundle_core:1 top_classes=content_changed:1",
            rendered,
        )
        self.assertIn(
            "pipeline_rejected_candidates: validator failed x2 (workflow-blueprint-pipeline-v131,workflow-blueprint-pipeline-v130); missing workflow_blueprint_pipeline_manifest.json x1 (workflow-blueprint-pipeline-v129)",
            rendered,
        )
        self.assertNotIn("candidate_rejections:\n-", rendered)
        self.assertNotIn("bundle_refresh_watch:", rendered)
        self.assertNotIn("bundle_refresh_history:", rendered)
        self.assertNotIn("bundle_refresh_stats:", rendered)
        self.assertNotIn("pipeline_rejected_candidates:\n-", rendered)
        self.assertNotIn("freshness_notes:\n-", rendered)

    def test_discover_current_stack_from_bundle_prefers_nested_bundle_outputs(self) -> None:
        bundle = self._make_bundle(self.root / "bundle-v3", clone_value="A", blueprint_value="B", nested=True)
        with mock.patch.object(stack_discovery, "run_validation", return_value=True):
            selected = stack_discovery.discover_current_stack_from_bundle(self.workdir, bundle)
        self.assertEqual(selected[0], bundle)
        self.assertEqual(selected[1], bundle / "workflow-blueprint-pipeline")
        self.assertEqual(selected[2], bundle / "workflow-blueprint-pipeline" / "workflow-runtime-bundle")

    def test_file_fingerprint_detects_same_size_content_change_via_sha256(self) -> None:
        path = self.root / "fingerprint.txt"
        path.write_text("abc\n", encoding="utf-8")
        original = manifest_utils.file_fingerprint(path)
        stat = path.stat()

        path.write_text("xyz\n", encoding="utf-8")
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        updated = manifest_utils.file_fingerprint(path)

        self.assertEqual(original["size"], updated["size"])
        self.assertEqual(original["mtime_ns"], updated["mtime_ns"])
        self.assertNotEqual(original["sha256"], updated["sha256"])
        self.assertNotEqual(original, updated)

    def test_refresh_dependency_registry_resolves_unique_absolute_paths(self) -> None:
        resolved = refresh_dependency_registry.resolve_refresh_dependencies(
            self.workdir,
            "bundle_core",
            "workflow_shared",
            "runtime_core",
        )
        self.assertTrue(resolved)
        self.assertEqual(len(resolved), len({str(path) for path in resolved}))
        self.assertTrue(all(path.is_absolute() for path in resolved))
        self.assertIn((self.workdir / "scripts" / "render_delivery_summary.py").resolve(), resolved)
        self.assertIn((self.workdir / "scripts" / "init_workflow_task_state.py").resolve(), resolved)

    def test_refresh_dependency_index_tracks_path_to_groups(self) -> None:
        index = refresh_dependency_registry.build_refresh_dependency_index(
            self.workdir,
            "workflow_shared",
            "runtime_core",
        )
        by_path = {str(item["path"]): item["groups"] for item in index}
        runtime_script = str((self.workdir / "scripts" / "bootstrap_workflow_clone_runtime.py").resolve())
        runtime_validation = str((self.workdir / "scripts" / "validate_profession_adapters.py").resolve())
        self.assertEqual(by_path[runtime_script], ["workflow_shared"])
        self.assertEqual(by_path[runtime_validation], ["runtime_core"])

    def test_diff_refresh_cache_classifies_metadata_only_and_deleted(self) -> None:
        metadata_path = self.root / "metadata-only.txt"
        deleted_path = self.root / "deleted.txt"
        metadata_path.write_text("same\n", encoding="utf-8")
        deleted_path.write_text("gone\n", encoding="utf-8")
        refresh_cache = manifest_utils.build_refresh_cache([metadata_path, deleted_path])
        manifest = {
            "refresh_cache": refresh_cache,
            "refresh_dependency_index": [
                {"path": str(metadata_path.resolve()), "groups": ["bundle_core"]},
                {"path": str(deleted_path.resolve()), "groups": ["workflow_shared"]},
            ],
        }

        stat = metadata_path.stat()
        metadata_path.write_text("same\n", encoding="utf-8")
        os.utime(metadata_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
        deleted_path.unlink()

        diff = manifest_utils.diff_refresh_cache(manifest)
        self.assertTrue(diff["changed"])
        self.assertEqual(diff["changed_class_counts"]["metadata_only"], 1)
        self.assertEqual(diff["changed_class_counts"]["deleted"], 1)
        by_name = {item["name"]: item for item in diff["changed_files"]}
        self.assertEqual(by_name["metadata-only.txt"]["change_class"], "metadata_only")
        self.assertEqual(by_name["deleted.txt"]["change_class"], "deleted")

    def test_merge_refresh_history_keeps_last_five_entries(self) -> None:
        previous_manifest = {
            "refresh_trigger_history": [{"reason": f"r{i}"} for i in range(5)],
            "last_refresh_trigger": {"reason": "ignored"},
        }
        merged = manifest_utils.merge_refresh_history(previous_manifest, {"reason": "r5"})
        self.assertEqual(len(merged), 5)
        self.assertEqual([item["reason"] for item in merged], ["r1", "r2", "r3", "r4", "r5"])

    def test_summarize_refresh_trigger_history_aggregates_recurring_files_groups_and_classes(self) -> None:
        stats = stack_discovery.summarize_refresh_trigger_history(
            [
                {
                    "changed_groups": ["bundle_core", "workflow_shared"],
                    "changed_classes": ["content_changed"],
                    "changed_files": [
                        {"name": "build_personal_clone_skill.py"},
                        {"name": "workflow_blueprint_template.md"},
                        {"name": "build_personal_clone_skill.py"},
                    ],
                },
                {
                    "changed_groups": ["bundle_core"],
                    "changed_classes": ["content_changed", "metadata_only"],
                    "changed_files": [
                        {"name": "build_personal_clone_skill.py"},
                        {"name": "working_clone_bundle_readme_template.md"},
                    ],
                },
                {
                    "changed_groups": ["workflow_shared"],
                    "changed_classes": ["metadata_only"],
                    "changed_files": [
                        {"name": "workflow_blueprint_template.md"},
                    ],
                },
            ]
        )

        self.assertEqual(stats["history_count"], 3)
        self.assertEqual(stats["top_files"][0], {"value": "build_personal_clone_skill.py", "count": 2})
        self.assertEqual(stats["top_files"][1], {"value": "workflow_blueprint_template.md", "count": 2})
        self.assertEqual(stats["top_groups"], [{"value": "bundle_core", "count": 2}, {"value": "workflow_shared", "count": 2}])
        self.assertEqual(stats["top_classes"], [{"value": "content_changed", "count": 2}, {"value": "metadata_only", "count": 2}])
        self.assertEqual(
            stack_discovery.render_refresh_history_stats(stats),
            "history=3 top_files=build_personal_clone_skill.py:2,workflow_blueprint_template.md:2,working_clone_bundle_readme_template.md:1 top_groups=bundle_core:2,workflow_shared:2 top_classes=content_changed:2,metadata_only:2",
        )

    def test_restore_refresh_metadata_if_missing_restores_snapshot_only_when_fields_are_empty(self) -> None:
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "last_refresh_trigger": {},
                    "refresh_trigger_history": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        snapshot = {
            "last_refresh_trigger": {"reason": "previous"},
            "refresh_trigger_history": [{"reason": "previous"}],
        }
        restored = manifest_utils.restore_refresh_metadata_if_missing(manifest_path, snapshot)
        self.assertEqual(restored["last_refresh_trigger"]["reason"], "previous")
        self.assertEqual(restored["refresh_trigger_history"][0]["reason"], "previous")

        manifest_path.write_text(
            json.dumps(
                {
                    "last_refresh_trigger": {"reason": "current"},
                    "refresh_trigger_history": [{"reason": "current"}],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        preserved = manifest_utils.restore_refresh_metadata_if_missing(manifest_path, snapshot)
        self.assertEqual(preserved["last_refresh_trigger"]["reason"], "current")
        self.assertEqual(preserved["refresh_trigger_history"][0]["reason"], "current")

    def test_filter_refresh_report_to_groups_keeps_only_matching_files_and_groups(self) -> None:
        filtered = manifest_utils.filter_refresh_report_to_groups(
            {
                "changed": True,
                "reason": "tracked_inputs_changed",
                "changed_files": [
                    {
                        "name": "build_personal_clone_skill.py",
                        "groups": ["bundle_core"],
                        "change_class": "content_changed",
                    },
                    {
                        "name": "workflow_blueprint_pipeline_readme_template.md",
                        "groups": ["workflow_shared"],
                        "change_class": "content_changed",
                    },
                    {
                        "name": "bootstrap_workflow_clone_runtime.py",
                        "groups": ["workflow_shared", "runtime_core"],
                        "change_class": "content_changed",
                    },
                ],
            },
            ["workflow_shared"],
            reason="propagated_from_parent_refresh",
        )

        self.assertEqual(filtered["reason"], "propagated_from_parent_refresh")
        self.assertEqual(filtered["changed_groups"], ["workflow_shared"])
        self.assertEqual(filtered["changed_count"], 2)
        self.assertEqual(
            [item["name"] for item in filtered["changed_files"]],
            [
                "workflow_blueprint_pipeline_readme_template.md",
                "bootstrap_workflow_clone_runtime.py",
            ],
        )
        self.assertTrue(all(item["groups"] == ["workflow_shared"] for item in filtered["changed_files"]))

    def test_propagate_refresh_to_manifest_appends_filtered_trigger(self) -> None:
        manifest_path = self.root / "pipeline.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "refresh_dependency_groups": ["workflow_shared"],
                    "refresh_trigger_history": [{"reason": "before"}],
                    "last_refresh_trigger": {"reason": "before"},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        manifest_utils.propagate_refresh_to_manifest(
            manifest_path,
            {
                "changed": True,
                "reason": "tracked_inputs_changed",
                "changed_files": [
                    {
                        "name": "build_personal_clone_skill.py",
                        "groups": ["bundle_core"],
                        "change_class": "content_changed",
                    },
                    {
                        "name": "workflow_blueprint_pipeline_readme_template.md",
                        "groups": ["workflow_shared"],
                        "change_class": "content_changed",
                    },
                ],
            },
            reason="propagated_from_bundle_refresh",
        )
        propagated = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(propagated["last_refresh_trigger"]["reason"], "propagated_from_bundle_refresh")
        self.assertEqual(propagated["last_refresh_trigger"]["changed_groups"], ["workflow_shared"])
        self.assertEqual(
            propagated["last_refresh_trigger"]["changed_files"][0]["name"],
            "workflow_blueprint_pipeline_readme_template.md",
        )
        self.assertEqual(len(propagated["refresh_trigger_history"]), 2)

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _make_bundle(self, root: Path, clone_value: str, blueprint_value: str, nested: bool = False) -> Path:
        personal_dir = root / "personal-clone-skill"
        pipeline_dir = root / "workflow-blueprint-pipeline"
        runtime_dir = pipeline_dir / "workflow-runtime-bundle"
        workflow_skill_dir = pipeline_dir / "workflow-clone-skill"
        clone_config = personal_dir / "clone_config.yaml"
        blueprint = pipeline_dir / "workflow_blueprint.md"
        clone_config.parent.mkdir(parents=True, exist_ok=True)
        blueprint.parent.mkdir(parents=True, exist_ok=True)
        clone_config.write_text(f"clone={clone_value}\n", encoding="utf-8")
        blueprint.write_text(f"blueprint={blueprint_value}\n", encoding="utf-8")
        (root / "working_clone_until_final_summary.json").write_text("{}\n", encoding="utf-8")
        (root / "WORKING_CLONE_BUNDLE_README.md").write_text("bundle\n", encoding="utf-8")
        self._write_json(
            root / "working_clone_bundle_manifest.json",
            {
                "workflow_blueprint": str(blueprint),
            },
        )
        if nested:
            self._make_pipeline(pipeline_dir, clone_value=clone_value, blueprint_value=blueprint_value)
            self._make_runtime(runtime_dir, clone_value=clone_value, blueprint_value=blueprint_value)
            self._make_personal_skill(personal_dir, clone_value=clone_value)
            self._make_workflow_skill(workflow_skill_dir, clone_value=clone_value, blueprint_value=blueprint_value)
        return root

    def _make_pipeline(self, root: Path, clone_value: str, blueprint_value: str) -> Path:
        clone_config = root / "source_clone_config.yaml"
        blueprint = root / "workflow_blueprint.md"
        clone_config.parent.mkdir(parents=True, exist_ok=True)
        clone_config.write_text(f"clone={clone_value}\n", encoding="utf-8")
        blueprint.write_text(f"blueprint={blueprint_value}\n", encoding="utf-8")
        (root / "WORKFLOW_BLUEPRINT_PIPELINE_README.md").write_text("pipeline\n", encoding="utf-8")
        self._write_json(
            root / "workflow_blueprint_pipeline_manifest.json",
            {
                "clone_config": str(clone_config),
                "blueprint": str(blueprint),
            },
        )
        return root

    def _make_runtime(self, root: Path, clone_value: str, blueprint_value: str) -> Path:
        clone_config = root / "source_clone_config.yaml"
        blueprint = root / "source_workflow_blueprint.md"
        clone_config.parent.mkdir(parents=True, exist_ok=True)
        clone_config.write_text(f"clone={clone_value}\n", encoding="utf-8")
        blueprint.write_text(f"blueprint={blueprint_value}\n", encoding="utf-8")
        (root / "WORKFLOW_RUNTIME_README.md").write_text("runtime\n", encoding="utf-8")
        self._write_json(
            root / "workflow_runtime_manifest.json",
            {
                "clone_config": str(clone_config),
                "workflow_blueprint": str(blueprint),
            },
        )
        return root

    def _make_personal_skill(self, root: Path, clone_value: str) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "clone_config.yaml").write_text(f"clone={clone_value}\n", encoding="utf-8")
        (root / "README.md").write_text("personal\n", encoding="utf-8")
        self._write_json(root / "personal_clone_skill_manifest.json", {"files": {"clone_config": str(root / "clone_config.yaml")}})
        return root

    def _make_workflow_skill(self, root: Path, clone_value: str, blueprint_value: str) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        (root / "clone_config.yaml").write_text(f"clone={clone_value}\n", encoding="utf-8")
        (root / "workflow_blueprint.md").write_text(f"blueprint={blueprint_value}\n", encoding="utf-8")
        (root / "README.md").write_text("workflow\n", encoding="utf-8")
        self._write_json(
            root / "workflow_clone_skill_manifest.json",
            {
                "files": {
                    "clone_config": str(root / "clone_config.yaml"),
                    "workflow_blueprint": str(root / "workflow_blueprint.md"),
                }
            },
        )
        return root


if __name__ == "__main__":
    unittest.main()
