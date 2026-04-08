#!/usr/bin/env python3
"""Central registry for manifest refresh dependencies."""

from __future__ import annotations

from pathlib import Path


REFRESH_DEPENDENCY_GROUPS: dict[str, tuple[str, ...]] = {
    "bundle_core": (
        "templates/working_clone_bundle_readme_template.md",
        "templates/personal_clone_skill_readme_template.md",
        "assets/personal-clone-skill-base/SKILL.md",
        "scripts/bootstrap_working_clone_bundle.py",
        "scripts/build_clone_from_artifacts.py",
        "scripts/build_personal_clone_skill.py",
        "scripts/validate_working_clone_bundle.py",
        "scripts/working_clone_dispatch.py",
        "scripts/plan_clone_interview_next.py",
        "scripts/init_clone_interview_state.py",
        "scripts/build_next_interview_update.py",
        "scripts/build_pending_interview_actions.py",
        "scripts/validate_clone_interview_state.py",
        "scripts/workflow_target_utils.py",
        "scripts/render_delivery_summary.py",
    ),
    "workflow_shared": (
        "templates/workflow_blueprint_template.md",
        "templates/workflow_blueprint_pipeline_readme_template.md",
        "templates/workflow_clone_skill_readme_template.md",
        "templates/workflow_runtime_readme_template.md",
        "assets/workflow-clone-skill-base/SKILL.md",
        "scripts/bootstrap_workflow_blueprint.py",
        "scripts/build_workflow_stage_confirmation.py",
        "scripts/extract_workflow_draft.py",
        "scripts/build_workflow_blueprint.py",
        "scripts/build_workflow_clone_skill.py",
        "scripts/bootstrap_workflow_clone_runtime.py",
        "scripts/validate_workflow_interview.py",
        "scripts/workflow_pipeline_dispatch.py",
        "scripts/workflow_runtime_dispatch.py",
        "scripts/profession_adapter_runtime.py",
    ),
    "runtime_core": (
        "scripts/init_workflow_task_state.py",
        "scripts/validate_profession_adapters.py",
    ),
}


def resolve_refresh_dependencies(root: Path, *group_names: str) -> list[Path]:
    resolved: list[Path] = []
    seen: set[str] = set()
    for group_name in group_names:
        members = REFRESH_DEPENDENCY_GROUPS.get(group_name)
        if members is None:
            raise ValueError(f"unknown refresh dependency group: {group_name}")
        for relative_path in members:
            path = (root / relative_path).resolve()
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(path)
    return resolved


def build_refresh_dependency_index(root: Path, *group_names: str) -> list[dict[str, object]]:
    grouped: dict[str, set[str]] = {}
    ordered_paths: list[str] = []
    for group_name in group_names:
        members = REFRESH_DEPENDENCY_GROUPS.get(group_name)
        if members is None:
            raise ValueError(f"unknown refresh dependency group: {group_name}")
        for relative_path in members:
            path = (root / relative_path).resolve()
            key = str(path)
            if key not in grouped:
                grouped[key] = set()
                ordered_paths.append(key)
            grouped[key].add(group_name)
    return [{"path": key, "groups": sorted(grouped[key])} for key in ordered_paths]
