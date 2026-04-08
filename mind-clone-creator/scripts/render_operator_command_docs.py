#!/usr/bin/env python3
"""Render operator command docs from a structured JSON source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


DEFAULT_SOURCE = repo_root() / "references" / "operator_commands.json"
DEFAULT_CONTRACT = repo_root() / "references" / "operator_command_contract.md"
DEFAULT_SUMMARY = repo_root() / "references" / "operator_command_summary.md"
DEFAULT_README = repo_root() / "README.md"
DEFAULT_PLAYBOOK = repo_root() / "references" / "operator_playbook.md"
DEFAULT_NEW_MAINTAINER = repo_root() / "references" / "new_maintainer_first_15_minutes.md"
DEFAULT_RELEASE_CHECKLIST = repo_root() / "RELEASE_READINESS_CHECKLIST.md"
DEFAULT_CURRENT_FLOW = repo_root() / "references" / "current_system_flow.md"
DEFAULT_CAPABILITY_INDEX = repo_root() / "references" / "capability_index.md"
DEFAULT_DOC_ROUTER = repo_root() / "references" / "doc_router.md"
DEFAULT_FAILURE_GUIDE = repo_root() / "references" / "failure_path_guide.md"

README_COMMAND_BLOCK_START = "<!-- BEGIN GENERATED: operator-command-quickstart -->"
README_COMMAND_BLOCK_END = "<!-- END GENERATED: operator-command-quickstart -->"
README_COMMAND_COVERAGE_START = "<!-- BEGIN GENERATED: operator-command-coverage -->"
README_COMMAND_COVERAGE_END = "<!-- END GENERATED: operator-command-coverage -->"
PLAYBOOK_DAILY_PATH_START = "<!-- BEGIN GENERATED: operator-playbook-daily-path -->"
PLAYBOOK_DAILY_PATH_END = "<!-- END GENERATED: operator-playbook-daily-path -->"
PLAYBOOK_RELEASE_CORE_START = "<!-- BEGIN GENERATED: operator-playbook-release-core -->"
PLAYBOOK_RELEASE_CORE_END = "<!-- END GENERATED: operator-playbook-release-core -->"
PLAYBOOK_RELEASE_VARIANTS_START = "<!-- BEGIN GENERATED: operator-playbook-release-variants -->"
PLAYBOOK_RELEASE_VARIANTS_END = "<!-- END GENERATED: operator-playbook-release-variants -->"
PLAYBOOK_RELEASE_BEHAVIOR_START = "<!-- BEGIN GENERATED: operator-playbook-release-behavior -->"
PLAYBOOK_RELEASE_BEHAVIOR_END = "<!-- END GENERATED: operator-playbook-release-behavior -->"
PLAYBOOK_REFRESH_START = "<!-- BEGIN GENERATED: operator-playbook-refresh-entry -->"
PLAYBOOK_REFRESH_END = "<!-- END GENERATED: operator-playbook-refresh-entry -->"
NEW_MAINTAINER_PREFLIGHT_START = "<!-- BEGIN GENERATED: new-maintainer-preflight -->"
NEW_MAINTAINER_PREFLIGHT_END = "<!-- END GENERATED: new-maintainer-preflight -->"
NEW_MAINTAINER_OPERATOR_PATH_START = "<!-- BEGIN GENERATED: new-maintainer-operator-path -->"
NEW_MAINTAINER_OPERATOR_PATH_END = "<!-- END GENERATED: new-maintainer-operator-path -->"
NEW_MAINTAINER_MAP_READING_START = "<!-- BEGIN GENERATED: new-maintainer-map-reading -->"
NEW_MAINTAINER_MAP_READING_END = "<!-- END GENERATED: new-maintainer-map-reading -->"
NEW_MAINTAINER_MAP_GOALS_START = "<!-- BEGIN GENERATED: new-maintainer-map-goals -->"
NEW_MAINTAINER_MAP_GOALS_END = "<!-- END GENERATED: new-maintainer-map-goals -->"
NEW_MAINTAINER_CONFIRM_START = "<!-- BEGIN GENERATED: new-maintainer-confirm -->"
NEW_MAINTAINER_CONFIRM_END = "<!-- END GENERATED: new-maintainer-confirm -->"
NEW_MAINTAINER_FAILURE_START = "<!-- BEGIN GENERATED: new-maintainer-failure-steps -->"
NEW_MAINTAINER_FAILURE_END = "<!-- END GENERATED: new-maintainer-failure-steps -->"
NEW_MAINTAINER_AFTER_15_START = "<!-- BEGIN GENERATED: new-maintainer-after-15 -->"
NEW_MAINTAINER_AFTER_15_END = "<!-- END GENERATED: new-maintainer-after-15 -->"
RELEASE_CHECKLIST_METADATA_START = "<!-- BEGIN GENERATED: release-checklist-metadata-commands -->"
RELEASE_CHECKLIST_METADATA_END = "<!-- END GENERATED: release-checklist-metadata-commands -->"
RELEASE_CHECKLIST_VALIDATION_START = "<!-- BEGIN GENERATED: release-checklist-validation-commands -->"
RELEASE_CHECKLIST_VALIDATION_END = "<!-- END GENERATED: release-checklist-validation-commands -->"
RELEASE_CHECKLIST_HANDOFF_START = "<!-- BEGIN GENERATED: release-checklist-handoff-items -->"
RELEASE_CHECKLIST_HANDOFF_END = "<!-- END GENERATED: release-checklist-handoff-items -->"
CURRENT_FLOW_EXAMPLES_START = "<!-- BEGIN GENERATED: current-flow-short-examples -->"
CURRENT_FLOW_EXAMPLES_END = "<!-- END GENERATED: current-flow-short-examples -->"
CURRENT_FLOW_ENTRY_CHOICES_START = "<!-- BEGIN GENERATED: current-flow-entry-choices -->"
CURRENT_FLOW_ENTRY_CHOICES_END = "<!-- END GENERATED: current-flow-entry-choices -->"
CURRENT_FLOW_OPERATOR_ROUTE_START = "<!-- BEGIN GENERATED: current-flow-operator-route -->"
CURRENT_FLOW_OPERATOR_ROUTE_END = "<!-- END GENERATED: current-flow-operator-route -->"
CURRENT_FLOW_PERSONA_FILES_START = "<!-- BEGIN GENERATED: current-flow-persona-files -->"
CURRENT_FLOW_PERSONA_FILES_END = "<!-- END GENERATED: current-flow-persona-files -->"
CURRENT_FLOW_OPERATOR_FILES_START = "<!-- BEGIN GENERATED: current-flow-operator-files -->"
CURRENT_FLOW_OPERATOR_FILES_END = "<!-- END GENERATED: current-flow-operator-files -->"
CURRENT_FLOW_OPERATOR_CHAIN_START = "<!-- BEGIN GENERATED: current-flow-operator-chain -->"
CURRENT_FLOW_OPERATOR_CHAIN_END = "<!-- END GENERATED: current-flow-operator-chain -->"
CURRENT_FLOW_WORKFLOW_FILES_START = "<!-- BEGIN GENERATED: current-flow-workflow-files -->"
CURRENT_FLOW_WORKFLOW_FILES_END = "<!-- END GENERATED: current-flow-workflow-files -->"
CURRENT_FLOW_PERSONA_STOPS_START = "<!-- BEGIN GENERATED: current-flow-persona-stops -->"
CURRENT_FLOW_PERSONA_STOPS_END = "<!-- END GENERATED: current-flow-persona-stops -->"
CURRENT_FLOW_PIPELINE_STOPS_START = "<!-- BEGIN GENERATED: current-flow-pipeline-stops -->"
CURRENT_FLOW_PIPELINE_STOPS_END = "<!-- END GENERATED: current-flow-pipeline-stops -->"
CURRENT_FLOW_RUNTIME_STOPS_START = "<!-- BEGIN GENERATED: current-flow-runtime-stops -->"
CURRENT_FLOW_RUNTIME_STOPS_END = "<!-- END GENERATED: current-flow-runtime-stops -->"
CURRENT_FLOW_OPERATOR_STOPS_START = "<!-- BEGIN GENERATED: current-flow-operator-stops -->"
CURRENT_FLOW_OPERATOR_STOPS_END = "<!-- END GENERATED: current-flow-operator-stops -->"
CURRENT_FLOW_PERSONA_RESUME_START = "<!-- BEGIN GENERATED: current-flow-persona-resume -->"
CURRENT_FLOW_PERSONA_RESUME_END = "<!-- END GENERATED: current-flow-persona-resume -->"
CURRENT_FLOW_PIPELINE_RESUME_START = "<!-- BEGIN GENERATED: current-flow-pipeline-resume -->"
CURRENT_FLOW_PIPELINE_RESUME_END = "<!-- END GENERATED: current-flow-pipeline-resume -->"
CURRENT_FLOW_RUNTIME_RESUME_START = "<!-- BEGIN GENERATED: current-flow-runtime-resume -->"
CURRENT_FLOW_RUNTIME_RESUME_END = "<!-- END GENERATED: current-flow-runtime-resume -->"
CURRENT_FLOW_OPERATOR_RESUME_START = "<!-- BEGIN GENERATED: current-flow-operator-resume -->"
CURRENT_FLOW_OPERATOR_RESUME_END = "<!-- END GENERATED: current-flow-operator-resume -->"
CAPABILITY_INDEX_ENTRY_START = "<!-- BEGIN GENERATED: capability-index-operator-entry -->"
CAPABILITY_INDEX_ENTRY_END = "<!-- END GENERATED: capability-index-operator-entry -->"
CAPABILITY_INDEX_CAPABILITIES_START = "<!-- BEGIN GENERATED: capability-index-operator-capabilities -->"
CAPABILITY_INDEX_CAPABILITIES_END = "<!-- END GENERATED: capability-index-operator-capabilities -->"
CAPABILITY_INDEX_RECENT_RELEASE_BEHAVIOR_START = "<!-- BEGIN GENERATED: capability-index-recent-release-behavior -->"
CAPABILITY_INDEX_RECENT_RELEASE_BEHAVIOR_END = "<!-- END GENERATED: capability-index-recent-release-behavior -->"
DOC_ROUTER_QUESTION_TABLE_START = "<!-- BEGIN GENERATED: doc-router-question-table -->"
DOC_ROUTER_QUESTION_TABLE_END = "<!-- END GENERATED: doc-router-question-table -->"
DOC_ROUTER_USER_VALUE_PATH_START = "<!-- BEGIN GENERATED: doc-router-user-value-path -->"
DOC_ROUTER_USER_VALUE_PATH_END = "<!-- END GENERATED: doc-router-user-value-path -->"
DOC_ROUTER_WORKFLOW_PATH_START = "<!-- BEGIN GENERATED: doc-router-workflow-path -->"
DOC_ROUTER_WORKFLOW_PATH_END = "<!-- END GENERATED: doc-router-workflow-path -->"
DOC_ROUTER_MAINTAINER_PATH_START = "<!-- BEGIN GENERATED: doc-router-maintainer-reading-path -->"
DOC_ROUTER_MAINTAINER_PATH_END = "<!-- END GENERATED: doc-router-maintainer-reading-path -->"
DOC_ROUTER_SINGLE_READ_START = "<!-- BEGIN GENERATED: doc-router-single-read -->"
DOC_ROUTER_SINGLE_READ_END = "<!-- END GENERATED: doc-router-single-read -->"
FAILURE_GUIDE_RELEASE_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-release-commands -->"
FAILURE_GUIDE_RELEASE_COMMANDS_END = "<!-- END GENERATED: failure-guide-release-commands -->"
FAILURE_GUIDE_RELEASE_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-release-inspect -->"
FAILURE_GUIDE_RELEASE_INSPECT_END = "<!-- END GENERATED: failure-guide-release-inspect -->"
FAILURE_GUIDE_RELEASE_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-release-next-steps -->"
FAILURE_GUIDE_RELEASE_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-release-next-steps -->"
FAILURE_GUIDE_LATEST_STACK_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-latest-stack-commands -->"
FAILURE_GUIDE_LATEST_STACK_COMMANDS_END = "<!-- END GENERATED: failure-guide-latest-stack-commands -->"
FAILURE_GUIDE_LATEST_STACK_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-latest-stack-next-steps -->"
FAILURE_GUIDE_LATEST_STACK_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-latest-stack-next-steps -->"
FAILURE_GUIDE_PERSONAL_EMPTY_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-personal-empty-inspect -->"
FAILURE_GUIDE_PERSONAL_EMPTY_INSPECT_END = "<!-- END GENERATED: failure-guide-personal-empty-inspect -->"
FAILURE_GUIDE_PERSONAL_EMPTY_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-personal-empty-next-steps -->"
FAILURE_GUIDE_PERSONAL_EMPTY_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-personal-empty-next-steps -->"
FAILURE_GUIDE_NEXT_INTERVIEW_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-next-interview-inspect -->"
FAILURE_GUIDE_NEXT_INTERVIEW_INSPECT_END = "<!-- END GENERATED: failure-guide-next-interview-inspect -->"
FAILURE_GUIDE_NEXT_INTERVIEW_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-next-interview-next-steps -->"
FAILURE_GUIDE_NEXT_INTERVIEW_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-next-interview-next-steps -->"
FAILURE_GUIDE_EVAL_DRAFT_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-eval-draft-inspect -->"
FAILURE_GUIDE_EVAL_DRAFT_INSPECT_END = "<!-- END GENERATED: failure-guide-eval-draft-inspect -->"
FAILURE_GUIDE_EVAL_DRAFT_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-eval-draft-next-steps -->"
FAILURE_GUIDE_EVAL_DRAFT_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-eval-draft-next-steps -->"
FAILURE_GUIDE_WORKFLOW_BLOCKER_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-commands -->"
FAILURE_GUIDE_WORKFLOW_BLOCKER_COMMANDS_END = "<!-- END GENERATED: failure-guide-workflow-blocker-commands -->"
FAILURE_GUIDE_WORKFLOW_BLOCKER_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-inspect -->"
FAILURE_GUIDE_WORKFLOW_BLOCKER_INSPECT_END = "<!-- END GENERATED: failure-guide-workflow-blocker-inspect -->"
FAILURE_GUIDE_BLUEPRINT_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-blueprint-commands -->"
FAILURE_GUIDE_BLUEPRINT_COMMANDS_END = "<!-- END GENERATED: failure-guide-blueprint-commands -->"
FAILURE_GUIDE_BLUEPRINT_REASONS_START = "<!-- BEGIN GENERATED: failure-guide-blueprint-reasons -->"
FAILURE_GUIDE_BLUEPRINT_REASONS_END = "<!-- END GENERATED: failure-guide-blueprint-reasons -->"
FAILURE_GUIDE_BLUEPRINT_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-blueprint-next-steps -->"
FAILURE_GUIDE_BLUEPRINT_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-blueprint-next-steps -->"
FAILURE_GUIDE_PERSONAL_EMPTY_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-personal-empty-commands -->"
FAILURE_GUIDE_PERSONAL_EMPTY_COMMANDS_END = "<!-- END GENERATED: failure-guide-personal-empty-commands -->"
FAILURE_GUIDE_NEXT_INTERVIEW_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-next-interview-commands -->"
FAILURE_GUIDE_NEXT_INTERVIEW_COMMANDS_END = "<!-- END GENERATED: failure-guide-next-interview-commands -->"
FAILURE_GUIDE_EVAL_DRAFT_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-eval-draft-commands -->"
FAILURE_GUIDE_EVAL_DRAFT_COMMANDS_END = "<!-- END GENERATED: failure-guide-eval-draft-commands -->"
FAILURE_GUIDE_WORKFLOW_BLOCKER_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-workflow-blocker-next-steps -->"
FAILURE_GUIDE_WORKFLOW_BLOCKER_STEPS_END = "<!-- END GENERATED: failure-guide-workflow-blocker-next-steps -->"
FAILURE_GUIDE_STAGE_CONFIRMATION_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-inspect -->"
FAILURE_GUIDE_STAGE_CONFIRMATION_INSPECT_END = "<!-- END GENERATED: failure-guide-stage-confirmation-inspect -->"
FAILURE_GUIDE_STAGE_CONFIRMATION_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-next-steps -->"
FAILURE_GUIDE_STAGE_CONFIRMATION_STEPS_END = "<!-- END GENERATED: failure-guide-stage-confirmation-next-steps -->"
FAILURE_GUIDE_BLUEPRINT_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-blueprint-inspect -->"
FAILURE_GUIDE_BLUEPRINT_INSPECT_END = "<!-- END GENERATED: failure-guide-blueprint-inspect -->"
FAILURE_GUIDE_LATEST_STACK_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-latest-stack-inspect -->"
FAILURE_GUIDE_LATEST_STACK_INSPECT_END = "<!-- END GENERATED: failure-guide-latest-stack-inspect -->"
FAILURE_GUIDE_STAGE_CONFIRMATION_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-stage-confirmation-commands -->"
FAILURE_GUIDE_STAGE_CONFIRMATION_COMMANDS_END = "<!-- END GENERATED: failure-guide-stage-confirmation-commands -->"
FAILURE_GUIDE_RUNTIME_INSPECT_START = "<!-- BEGIN GENERATED: failure-guide-runtime-inspect -->"
FAILURE_GUIDE_RUNTIME_INSPECT_END = "<!-- END GENERATED: failure-guide-runtime-inspect -->"
FAILURE_GUIDE_RUNTIME_NEXT_STEPS_START = "<!-- BEGIN GENERATED: failure-guide-runtime-next-steps -->"
FAILURE_GUIDE_RUNTIME_NEXT_STEPS_END = "<!-- END GENERATED: failure-guide-runtime-next-steps -->"
FAILURE_GUIDE_RUNTIME_COMMANDS_START = "<!-- BEGIN GENERATED: failure-guide-runtime-commands -->"
FAILURE_GUIDE_RUNTIME_COMMANDS_END = "<!-- END GENERATED: failure-guide-runtime-commands -->"
FAILURE_GUIDE_QUICK_REFERENCE_START = "<!-- BEGIN GENERATED: failure-guide-quick-reference -->"
FAILURE_GUIDE_QUICK_REFERENCE_END = "<!-- END GENERATED: failure-guide-quick-reference -->"
FAILURE_GUIDE_READING_ORDER_START = "<!-- BEGIN GENERATED: failure-guide-reading-order -->"
FAILURE_GUIDE_READING_ORDER_END = "<!-- END GENERATED: failure-guide-reading-order -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render operator command docs from JSON.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--contract-output", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--summary-output", default=str(DEFAULT_SUMMARY))
    parser.add_argument("--readme-output", default=str(DEFAULT_README))
    parser.add_argument("--playbook-output", default=str(DEFAULT_PLAYBOOK))
    parser.add_argument("--new-maintainer-output", default=str(DEFAULT_NEW_MAINTAINER))
    parser.add_argument("--release-checklist-output", default=str(DEFAULT_RELEASE_CHECKLIST))
    parser.add_argument("--current-flow-output", default=str(DEFAULT_CURRENT_FLOW))
    parser.add_argument("--capability-index-output", default=str(DEFAULT_CAPABILITY_INDEX))
    parser.add_argument("--doc-router-output", default=str(DEFAULT_DOC_ROUTER))
    parser.add_argument("--failure-guide-output", default=str(DEFAULT_FAILURE_GUIDE))
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def load_source(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def ensure_named_string_map(source: dict[str, Any], key: str) -> dict[str, str]:
    raw = source.get(key, {})
    if not isinstance(raw, dict):
        raise SystemExit(f"operator_commands.json: {key} must be an object")
    resolved: dict[str, str] = {}
    for item_key, value in raw.items():
        name = str(item_key).strip()
        text = str(value).strip()
        if not name or not text:
            raise SystemExit(f"operator_commands.json: {key} entries must be non-empty strings")
        resolved[name] = text
    return resolved


def resolve_named_string_value(
    source: dict[str, Any],
    raw_value: Any,
    *,
    map_name: str,
    ref_key: str,
    field_name: str,
) -> str:
    if isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            raise SystemExit(f"operator_commands.json: empty value in {field_name}")
        return value
    if not isinstance(raw_value, dict):
        raise SystemExit(f"operator_commands.json: {field_name} must be a string or {ref_key} object")
    ref_name = str(raw_value.get(ref_key, "")).strip()
    if not ref_name:
        raise SystemExit(f"operator_commands.json: {field_name} ref objects must include {ref_key}")
    named_values = ensure_named_string_map(source, map_name)
    if ref_name not in named_values:
        raise SystemExit(f"operator_commands.json: unknown {ref_key} in {field_name}: {ref_name}")
    return named_values[ref_name]


def resolve_doc_path_value(source: dict[str, Any], raw_value: Any, field_name: str) -> str:
    return resolve_named_string_value(
        source,
        raw_value,
        map_name="doc_refs",
        ref_key="doc_ref",
        field_name=field_name,
    )


def resolve_inspect_text_value(source: dict[str, Any], raw_value: Any, field_name: str) -> str:
    return resolve_named_string_value(
        source,
        raw_value,
        map_name="inspect_refs",
        ref_key="inspect_ref",
        field_name=field_name,
    )


def resolve_object_doc_path_field(source: dict[str, Any], item: dict[str, Any], field_name: str) -> str:
    raw_value: Any = item.get("path", "") if "path" in item else {"doc_ref": item.get("doc_ref")}
    return resolve_doc_path_value(source, raw_value, field_name)


def ensure_command_map(source: dict[str, Any]) -> dict[str, dict[str, str]]:
    raw = source.get("commands", {})
    if not isinstance(raw, dict):
        raise SystemExit("operator_commands.json: commands must be an object")
    commands: dict[str, dict[str, str]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            raise SystemExit(f"operator_commands.json: command {key} must be an object")
        label = str(value.get("label", "")).strip()
        command = str(value.get("command", "")).strip()
        if not label or not command:
            raise SystemExit(f"operator_commands.json: command {key} must include label and command")
        payload = {"label": label, "command": command}
        surface = str(value.get("surface", "")).strip()
        if surface:
            payload["surface"] = surface
        route_surface = str(value.get("route_surface", "")).strip()
        if route_surface:
            payload["route_surface"] = route_surface
        commands[str(key)] = payload
    return commands


def resolve_command_ids(source: dict[str, Any], field: str, commands: dict[str, dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    raw_ids = source.get(field, [])
    if not isinstance(raw_ids, list):
        raise SystemExit(f"operator_commands.json: {field} must be a list")
    resolved: list[tuple[str, dict[str, str]]] = []
    for item in raw_ids:
        key = str(item).strip()
        if not key or key not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in {field}: {item}")
        resolved.append((key, commands[key]))
    return resolved


def resolve_summary_ids(source: dict[str, Any], key: str, commands: dict[str, dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    summary = source.get("summary", {})
    if not isinstance(summary, dict):
        raise SystemExit("operator_commands.json: summary must be an object")
    raw_ids = summary.get(key, [])
    if not isinstance(raw_ids, list):
        raise SystemExit(f"operator_commands.json: summary.{key} must be a list")
    resolved: list[tuple[str, dict[str, str]]] = []
    for item in raw_ids:
        item_key = str(item).strip()
        if not item_key or item_key not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in summary.{key}: {item}")
        resolved.append((item_key, commands[item_key]))
    return resolved


def resolve_section_command_ids(
    source: dict[str, Any], section_name: str, key: str, commands: dict[str, dict[str, str]]
) -> list[tuple[str, dict[str, str]]]:
    section = source.get(section_name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"operator_commands.json: {section_name} must be an object")
    raw_ids = section.get(key, [])
    if not isinstance(raw_ids, list):
        raise SystemExit(f"operator_commands.json: {section_name}.{key} must be a list")
    resolved: list[tuple[str, dict[str, str]]] = []
    for item in raw_ids:
        item_key = str(item).strip()
        if not item_key or item_key not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in {section_name}.{key}: {item}")
        resolved.append((item_key, commands[item_key]))
    return resolved


def resolve_readme_ids(source: dict[str, Any], key: str, commands: dict[str, dict[str, str]]) -> list[tuple[str, dict[str, str]]]:
    readme = source.get("readme", {})
    if not isinstance(readme, dict):
        raise SystemExit("operator_commands.json: readme must be an object")
    raw_ids = readme.get(key, [])
    if not isinstance(raw_ids, list):
        raise SystemExit(f"operator_commands.json: readme.{key} must be a list")
    resolved: list[tuple[str, dict[str, str]]] = []
    for item in raw_ids:
        item_key = str(item).strip()
        if not item_key or item_key not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in readme.{key}: {item}")
        resolved.append((item_key, commands[item_key]))
    return resolved


def resolve_section_items(
    source: dict[str, Any], section_name: str, key: str, commands: dict[str, dict[str, str]]
) -> list[tuple[str, dict[str, str]]]:
    section = source.get(section_name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"operator_commands.json: {section_name} must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: {section_name}.{key} must be a list")
    resolved: list[tuple[str, dict[str, str]]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit(f"operator_commands.json: {section_name}.{key} items must be objects")
        command_id = str(item.get("command_id", "")).strip()
        description = str(item.get("description", "")).strip()
        if not command_id or command_id not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in {section_name}.{key}: {item}")
        if not description:
            raise SystemExit(f"operator_commands.json: {section_name}.{key} items must include description")
        resolved.append((description, commands[command_id]))
    return resolved


def resolve_section_item_specs(
    source: dict[str, Any], section_name: str, key: str, commands: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    section = source.get(section_name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"operator_commands.json: {section_name} must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: {section_name}.{key} must be a list")
    resolved: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit(f"operator_commands.json: {section_name}.{key} items must be objects")
        command_id = str(item.get("command_id", "")).strip()
        description = str(item.get("description", "")).strip()
        if not command_id or command_id not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in {section_name}.{key}: {item}")
        if not description:
            raise SystemExit(f"operator_commands.json: {section_name}.{key} items must include description")
        resolved.append(
            {
                "command_id": command_id,
                "description": description,
                "payload": commands[command_id],
            }
        )
    return resolved


def resolve_section_strings(source: dict[str, Any], section_name: str, key: str) -> list[str]:
    section = source.get(section_name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"operator_commands.json: {section_name} must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: {section_name}.{key} must be a list")
    resolved: list[str] = []
    field_name = f"{section_name}.{key}"
    for item in raw_items:
        resolved.append(resolve_inspect_text_value(source, item, field_name))
    return resolved


def resolve_section_mixed_text_or_path_items(
    source: dict[str, Any], section_name: str, key: str
) -> list[dict[str, str]]:
    section = source.get(section_name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"operator_commands.json: {section_name} must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: {section_name}.{key} must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if isinstance(item, str):
            value = item.strip()
            if not value:
                raise SystemExit(f"operator_commands.json: empty item in {section_name}.{key}")
            resolved.append({"kind": "text", "text": value})
            continue
        if not isinstance(item, dict):
            raise SystemExit(f"operator_commands.json: {section_name}.{key} items must be strings or objects")
        prefix = str(item.get("prefix", "")).strip()
        suffix = str(item.get("suffix", "")).strip()
        if not prefix:
            raise SystemExit(f"operator_commands.json: {section_name}.{key} path items must include prefix")
        resolved.append(
            {
                "kind": "path",
                "prefix": prefix,
                "path": resolve_object_doc_path_field(source, item, f"{section_name}.{key}"),
                "suffix": suffix,
            }
        )
    return resolved


def resolve_failure_guide_reading_order_items(source: dict[str, Any]) -> list[dict[str, str]]:
    section = source.get("failure_guide", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: failure_guide must be an object")
    raw_items = section.get("recent_failure_reading_order_items", [])
    if not isinstance(raw_items, list):
        raise SystemExit("operator_commands.json: failure_guide.recent_failure_reading_order_items must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit(
                "operator_commands.json: failure_guide.recent_failure_reading_order_items items must be objects"
            )
        lead = str(item.get("lead", "")).strip()
        note = str(item.get("note", "")).strip()
        if not lead:
            raise SystemExit(
                "operator_commands.json: failure_guide.recent_failure_reading_order_items items must include lead"
            )
        path = resolve_object_doc_path_field(source, item, "failure_guide.recent_failure_reading_order_items")
        resolved.append({"lead": lead, "path": path, "note": note})
    return resolved


def resolve_doc_router_rows(source: dict[str, Any]) -> list[dict[str, str]]:
    section = source.get("doc_router", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: doc_router must be an object")
    raw_items = section.get("question_rows", [])
    if not isinstance(raw_items, list):
        raise SystemExit("operator_commands.json: doc_router.question_rows must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit("operator_commands.json: doc_router.question_rows items must be objects")
        question = str(item.get("question", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if not question or not reason:
            raise SystemExit("operator_commands.json: doc_router.question_rows items must include question and reason")
        path = resolve_object_doc_path_field(source, item, "doc_router.question_rows")
        resolved.append({"question": question, "path": path, "reason": reason})
    return resolved


def resolve_doc_router_paths(source: dict[str, Any], key: str) -> list[str]:
    section = source.get("doc_router", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: doc_router must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: doc_router.{key} must be a list")
    resolved: list[str] = []
    for item in raw_items:
        resolved.append(resolve_doc_path_value(source, item, f"doc_router.{key}"))
    return resolved


def resolve_doc_router_single_read_items(source: dict[str, Any]) -> list[dict[str, str]]:
    section = source.get("doc_router", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: doc_router must be an object")
    raw_items = section.get("single_read_items", [])
    if not isinstance(raw_items, list):
        raise SystemExit("operator_commands.json: doc_router.single_read_items must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit("operator_commands.json: doc_router.single_read_items items must be objects")
        label = str(item.get("label", "")).strip()
        if not label:
            raise SystemExit("operator_commands.json: doc_router.single_read_items items must include label")
        path = resolve_object_doc_path_field(source, item, "doc_router.single_read_items")
        resolved.append({"label": label, "path": path})
    return resolved


def resolve_section_paths(source: dict[str, Any], section_name: str, key: str) -> list[str]:
    section = source.get(section_name, {})
    if not isinstance(section, dict):
        raise SystemExit(f"operator_commands.json: {section_name} must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: {section_name}.{key} must be a list")
    resolved: list[str] = []
    for item in raw_items:
        resolved.append(resolve_doc_path_value(source, item, f"{section_name}.{key}"))
    return resolved


def resolve_current_flow_entry_rows(source: dict[str, Any]) -> list[dict[str, str]]:
    section = source.get("current_flow", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: current_flow must be an object")
    raw_items = section.get("entry_choice_rows", [])
    if not isinstance(raw_items, list):
        raise SystemExit("operator_commands.json: current_flow.entry_choice_rows must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit("operator_commands.json: current_flow.entry_choice_rows items must be objects")
        goal = str(item.get("goal", "")).strip()
        entry = str(item.get("entry", "")).strip()
        when = str(item.get("when", "")).strip()
        stop_point = str(item.get("stop_point", "")).strip()
        if not goal or not entry or not when or not stop_point:
            raise SystemExit(
                "operator_commands.json: current_flow.entry_choice_rows items must include goal, entry, when, and stop_point"
            )
        resolved.append({"goal": goal, "entry": entry, "when": when, "stop_point": stop_point})
    return resolved


def resolve_current_flow_file_rows(source: dict[str, Any], key: str) -> list[dict[str, str]]:
    section = source.get("current_flow", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: current_flow must be an object")
    raw_items = section.get(key, [])
    if not isinstance(raw_items, list):
        raise SystemExit(f"operator_commands.json: current_flow.{key} must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit(f"operator_commands.json: current_flow.{key} items must be objects")
        file_name = resolve_inspect_text_value(source, item.get("file", ""), f"current_flow.{key}.file")
        location = str(item.get("location", "")).strip()
        writer = str(item.get("writer", "")).strip()
        meaning = str(item.get("meaning", "")).strip()
        next_step = str(item.get("next_step", "")).strip()
        if not file_name or not location or not writer or not meaning or not next_step:
            raise SystemExit(f"operator_commands.json: current_flow.{key} items must include file, location, writer, meaning, and next_step")
        resolved.append(
            {
                "file": file_name,
                "location": location,
                "writer": writer,
                "meaning": meaning,
                "next_step": next_step,
            }
        )
    return resolved


def resolve_failure_guide_quick_reference_rows(source: dict[str, Any], commands: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    section = source.get("failure_guide", {})
    if not isinstance(section, dict):
        raise SystemExit("operator_commands.json: failure_guide must be an object")
    raw_items = section.get("quick_reference_rows", [])
    if not isinstance(raw_items, list):
        raise SystemExit("operator_commands.json: failure_guide.quick_reference_rows must be a list")
    resolved: list[dict[str, str]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise SystemExit("operator_commands.json: failure_guide.quick_reference_rows items must be objects")
        problem = str(item.get("problem", "")).strip()
        inspect = str(item.get("inspect", "")).strip()
        command_id = str(item.get("command_id", "")).strip()
        if not problem or not inspect or not command_id:
            raise SystemExit(
                "operator_commands.json: failure_guide.quick_reference_rows items must include problem, inspect, and command_id"
            )
        if command_id not in commands:
            raise SystemExit(f"operator_commands.json: unknown command id in failure_guide.quick_reference_rows: {command_id}")
        resolved.append({"problem": problem, "inspect": inspect, "command": commands[command_id]["command"]})
    return resolved


def render_bullets(items: list[tuple[str, dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for _, payload in items:
        lines.append(f"- {payload['label']}：")
        lines.append(f"  `{payload['command']}`")
    return lines


def render_described_bullets(items: list[tuple[str, dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for description, payload in items:
        lines.append(f"- {description}：")
        lines.append(f"  `{payload['command']}`")
    return lines


def render_surface_list(items: list[tuple[str, dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for _, payload in items:
        surface = payload.get("surface", payload["command"])
        lines.append(f"- `{surface}`")
    return lines


def render_numbered(items: list[tuple[str, dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for idx, (_, payload) in enumerate(items, start=1):
        lines.append(f"{idx}. `{payload['command']}`")
    return lines


def render_numbered_described(items: list[tuple[str, dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for idx, (description, payload) in enumerate(items, start=1):
        lines.append(f"{idx}. {description}：")
        lines.append(f"   `{payload['command']}`")
    return lines


def render_checkbox_commands(items: list[tuple[str, dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for _, payload in items:
        lines.append(f"- [ ] `{payload['command']}`")
    return lines


def render_arrow_surfaces(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(items):
        surface = item["payload"].get("route_surface", item["payload"].get("surface", item["payload"]["command"]))
        lines.append(f"`{surface}`")
        if idx < len(items) - 1:
            lines.append("→")
    return lines


def render_mermaid_chain(items: list[dict[str, Any]]) -> list[str]:
    lines = ["```mermaid", "flowchart LR"]
    nodes: list[tuple[str, str]] = []
    for idx, item in enumerate(items, start=1):
        node_id = f"N{idx}"
        label = item["payload"].get("route_surface", item["payload"].get("surface", item["payload"]["command"]))
        nodes.append((node_id, label))
    for idx in range(len(nodes) - 1):
        current_id, current_label = nodes[idx]
        next_id, next_label = nodes[idx + 1]
        lines.append(f"    {current_id}[{current_label}] --> {next_id}[{next_label}]")
    lines.append("```")
    return lines


def render_literal_bullets(items: list[str]) -> list[str]:
    return [f"- `{item}`" for item in items]


def render_text_bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_numbered_text(items: list[str]) -> list[str]:
    return [f"{idx}. {item}" for idx, item in enumerate(items, start=1)]


def render_doc_link(path_text: str) -> str:
    path = (repo_root() / path_text).resolve()
    return f"[{Path(path_text).name}]({path})"


def render_described_command_table(items: list[tuple[str, dict[str, str]]], heading: str, command_heading: str) -> list[str]:
    lines = [f"| {heading} | {command_heading} |", "| --- | --- |"]
    for description, payload in items:
        lines.append(f"| {description} | `{payload['command']}` |")
    return lines


def render_numbered_doc_links(items: list[str]) -> list[str]:
    return [f"{idx}. {render_doc_link(item)}" for idx, item in enumerate(items, start=1)]


def render_numbered_doc_steps(items: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        note = f" {item['note']}" if item["note"] else ""
        lines.append(f"{idx}. {item['lead']} {render_doc_link(item['path'])}{note}")
    return lines


def render_mixed_text_or_path_bullets(items: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for item in items:
        if item["kind"] == "text":
            lines.append(f"- {item['text']}")
            continue
        suffix = f" {item['suffix']}" if item.get("suffix") else ""
        lines.append(f"- {item['prefix']} {render_doc_link(item['path'])}{suffix}")
    return lines


def render_single_read_bullets(items: list[dict[str, str]]) -> list[str]:
    return [f"- {item['label']}：读 {render_doc_link(item['path'])}" for item in items]


def render_contract(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    canonical = resolve_command_ids(source, "canonical_command_ids", commands)
    daily = resolve_command_ids(source, "daily_stack_command_ids", commands)
    release = resolve_command_ids(source, "release_command_ids", commands)

    lines = [
        "# Operator Command Contract",
        "",
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "这份文档是 operator 命令的单一真源。",
        "",
        "如果 README、维护者入口、排障文档里只保留了命令名或缩写说明，以这里的命令行为准。以后命令语法改动，优先先改这份合同，再改其他引用文档。",
        "",
        "## Canonical Commands",
        "",
        *render_bullets(canonical),
        "",
        "## Daily Stack Commands",
        "",
        "最常用的日常顺序：",
        "",
        *render_numbered(daily),
        "",
        "## Release Commands",
        "",
        *render_bullets(release),
        "",
        "## 使用原则",
        "",
        "- 想知道“为什么用这条命令、失败后看哪里”，看 [operator_playbook.md](./operator_playbook.md)",
        "- 想知道“第一次接手维护先跑什么”，看 [new_maintainer_first_15_minutes.md](./new_maintainer_first_15_minutes.md)",
        "- 想知道“某个失败态下一步怎么排”，看 [failure_path_guide.md](./failure_path_guide.md)",
        "",
    ]
    return "\n".join(lines)


def render_summary(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    top = resolve_summary_ids(source, "top_command_ids", commands)
    stack_entries = resolve_summary_ids(source, "stack_entry_ids", commands)

    lines = [
        "# Operator Command Summary",
        "",
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "这份文档是从 operator 命令数据源自动生成的快速摘要，适合只想先扫一眼最常用命令的人。",
        "",
        "## 最常用的 4 条命令",
        "",
        *render_bullets(top),
        "",
        "## 常见 Stack 级入口",
        "",
        *render_bullets(stack_entries),
        "",
        "## 继续看",
        "",
        "- 完整命令合同： [operator_command_contract.md](./operator_command_contract.md)",
        "- 维护者解释与排障： [operator_playbook.md](./operator_playbook.md)",
        "- 第一次接手维护： [new_maintainer_first_15_minutes.md](./new_maintainer_first_15_minutes.md)",
        "",
    ]
    return "\n".join(lines)


def render_readme_quickstart_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    top = resolve_summary_ids(source, "top_command_ids", commands)

    lines = [
        README_COMMAND_BLOCK_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        f"最常用的 {len(top)} 条命令：",
        "",
        *render_bullets(top),
        README_COMMAND_BLOCK_END,
    ]
    return "\n".join(lines)


def render_readme_coverage_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    coverage = resolve_readme_ids(source, "coverage_command_ids", commands)

    lines = [
        README_COMMAND_COVERAGE_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "其中覆盖：",
        "",
        *render_surface_list(coverage),
        README_COMMAND_COVERAGE_END,
    ]
    return "\n".join(lines)


def render_playbook_daily_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "playbook", "daily_path_items", commands)
    lines = [
        PLAYBOOK_DAILY_PATH_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        PLAYBOOK_DAILY_PATH_END,
    ]
    return "\n".join(lines)


def render_playbook_release_core_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "playbook", "release_core_items", commands)
    lines = [
        PLAYBOOK_RELEASE_CORE_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        PLAYBOOK_RELEASE_CORE_END,
    ]
    return "\n".join(lines)


def render_playbook_release_variants_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "playbook", "release_variant_items", commands)
    lines = [
        PLAYBOOK_RELEASE_VARIANTS_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        PLAYBOOK_RELEASE_VARIANTS_END,
    ]
    return "\n".join(lines)


def render_playbook_release_behavior_block(source: dict[str, Any]) -> str:
    items = resolve_section_strings(source, "playbook", "release_behavior_lines")
    lines = [
        PLAYBOOK_RELEASE_BEHAVIOR_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_text_bullets(items),
        PLAYBOOK_RELEASE_BEHAVIOR_END,
    ]
    return "\n".join(lines)


def render_playbook_refresh_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "playbook", "refresh_entry_items", commands)
    lines = [
        PLAYBOOK_REFRESH_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        PLAYBOOK_REFRESH_END,
    ]
    return "\n".join(lines)


def render_operator_playbook(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                PLAYBOOK_DAILY_PATH_START,
                PLAYBOOK_DAILY_PATH_END,
                render_playbook_daily_block(source),
            ),
            (
                PLAYBOOK_RELEASE_CORE_START,
                PLAYBOOK_RELEASE_CORE_END,
                render_playbook_release_core_block(source),
            ),
            (
                PLAYBOOK_RELEASE_VARIANTS_START,
                PLAYBOOK_RELEASE_VARIANTS_END,
                render_playbook_release_variants_block(source),
            ),
            (
                PLAYBOOK_RELEASE_BEHAVIOR_START,
                PLAYBOOK_RELEASE_BEHAVIOR_END,
                render_playbook_release_behavior_block(source),
            ),
            (
                PLAYBOOK_REFRESH_START,
                PLAYBOOK_REFRESH_END,
                render_playbook_refresh_block(source),
            ),
        ],
    )


def render_new_maintainer_preflight_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "new_maintainer", "preflight_items", commands)
    lines = [
        NEW_MAINTAINER_PREFLIGHT_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        NEW_MAINTAINER_PREFLIGHT_END,
    ]
    return "\n".join(lines)


def render_new_maintainer_map_reading_block(source: dict[str, Any]) -> str:
    items = resolve_section_paths(source, "new_maintainer", "map_reading_paths")
    lines = [
        NEW_MAINTAINER_MAP_READING_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_doc_links(items),
        NEW_MAINTAINER_MAP_READING_END,
    ]
    return "\n".join(lines)


def render_new_maintainer_text_block(source: dict[str, Any], key: str, start_marker: str, end_marker: str) -> str:
    items = resolve_section_strings(source, "new_maintainer", key)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_text_bullets(items),
        end_marker,
    ]
    return "\n".join(lines)


def render_new_maintainer_failure_block(source: dict[str, Any]) -> str:
    items = resolve_section_mixed_text_or_path_items(source, "new_maintainer", "failure_items")
    lines = [
        NEW_MAINTAINER_FAILURE_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_mixed_text_or_path_bullets(items),
        NEW_MAINTAINER_FAILURE_END,
    ]
    return "\n".join(lines)


def render_new_maintainer_operator_path_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_command_ids(source, "new_maintainer", "operator_path_command_ids", commands)
    lines = [
        NEW_MAINTAINER_OPERATOR_PATH_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered(items),
        NEW_MAINTAINER_OPERATOR_PATH_END,
    ]
    return "\n".join(lines)


def render_new_maintainer(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                NEW_MAINTAINER_MAP_READING_START,
                NEW_MAINTAINER_MAP_READING_END,
                render_new_maintainer_map_reading_block(source),
            ),
            (
                NEW_MAINTAINER_MAP_GOALS_START,
                NEW_MAINTAINER_MAP_GOALS_END,
                render_new_maintainer_text_block(
                    source,
                    "map_goal_items",
                    NEW_MAINTAINER_MAP_GOALS_START,
                    NEW_MAINTAINER_MAP_GOALS_END,
                ),
            ),
            (
                NEW_MAINTAINER_PREFLIGHT_START,
                NEW_MAINTAINER_PREFLIGHT_END,
                render_new_maintainer_preflight_block(source),
            ),
            (
                NEW_MAINTAINER_OPERATOR_PATH_START,
                NEW_MAINTAINER_OPERATOR_PATH_END,
                render_new_maintainer_operator_path_block(source),
            ),
            (
                NEW_MAINTAINER_CONFIRM_START,
                NEW_MAINTAINER_CONFIRM_END,
                render_new_maintainer_text_block(
                    source,
                    "confirmation_items",
                    NEW_MAINTAINER_CONFIRM_START,
                    NEW_MAINTAINER_CONFIRM_END,
                ),
            ),
            (
                NEW_MAINTAINER_FAILURE_START,
                NEW_MAINTAINER_FAILURE_END,
                render_new_maintainer_failure_block(source),
            ),
            (
                NEW_MAINTAINER_AFTER_15_START,
                NEW_MAINTAINER_AFTER_15_END,
                render_new_maintainer_text_block(
                    source,
                    "after_15_minutes_items",
                    NEW_MAINTAINER_AFTER_15_START,
                    NEW_MAINTAINER_AFTER_15_END,
                ),
            ),
        ],
    )


def render_release_checklist_metadata_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_command_ids(source, "release_checklist", "metadata_command_ids", commands)
    lines = [
        RELEASE_CHECKLIST_METADATA_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_checkbox_commands(items),
        RELEASE_CHECKLIST_METADATA_END,
    ]
    return "\n".join(lines)


def render_release_checklist_validation_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_command_ids(source, "release_checklist", "validation_command_ids", commands)
    lines = [
        RELEASE_CHECKLIST_VALIDATION_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_checkbox_commands(items),
        RELEASE_CHECKLIST_VALIDATION_END,
    ]
    return "\n".join(lines)


def render_release_checklist_handoff_block(source: dict[str, Any]) -> str:
    items = [
        *resolve_section_strings(source, "release_checklist", "handoff_intro_items"),
        *resolve_section_strings(source, "playbook", "release_behavior_lines"),
        *resolve_section_strings(source, "release_checklist", "handoff_outro_items"),
    ]
    lines = [
        RELEASE_CHECKLIST_HANDOFF_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *[f"- [ ] {item}" for item in items],
        RELEASE_CHECKLIST_HANDOFF_END,
    ]
    return "\n".join(lines)


def render_release_checklist(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                RELEASE_CHECKLIST_METADATA_START,
                RELEASE_CHECKLIST_METADATA_END,
                render_release_checklist_metadata_block(source),
            ),
            (
                RELEASE_CHECKLIST_VALIDATION_START,
                RELEASE_CHECKLIST_VALIDATION_END,
                render_release_checklist_validation_block(source),
            ),
            (
                RELEASE_CHECKLIST_HANDOFF_START,
                RELEASE_CHECKLIST_HANDOFF_END,
                render_release_checklist_handoff_block(source),
            ),
        ],
    )


def render_current_flow_examples_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "current_flow", "short_example_items", commands)
    lines = [
        CURRENT_FLOW_EXAMPLES_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_described(items),
        CURRENT_FLOW_EXAMPLES_END,
    ]
    return "\n".join(lines)


def render_current_flow_entry_choices_block(source: dict[str, Any]) -> str:
    rows = resolve_current_flow_entry_rows(source)
    lines = [
        CURRENT_FLOW_ENTRY_CHOICES_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "| 你的目标 | 优先入口 | 什么时候用 | 典型停点 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['goal']} | {row['entry']} | {row['when']} | {row['stop_point']} |")
    lines.append(CURRENT_FLOW_ENTRY_CHOICES_END)
    return "\n".join(lines)


def render_current_flow_file_rows_block(
    source: dict[str, Any], key: str, start_marker: str, end_marker: str
) -> str:
    rows = resolve_current_flow_file_rows(source, key)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "| 文件 | 典型位置 | 首次由谁写出 | 它表示什么 | 常见下一步 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['file']} | {row['location']} | {row['writer']} | {row['meaning']} | {row['next_step']} |"
        )
    lines.append(end_marker)
    return "\n".join(lines)


def render_current_flow_persona_files_block(source: dict[str, Any]) -> str:
    return render_current_flow_file_rows_block(
        source,
        "persona_file_rows",
        CURRENT_FLOW_PERSONA_FILES_START,
        CURRENT_FLOW_PERSONA_FILES_END,
    )


def render_current_flow_workflow_files_block(source: dict[str, Any]) -> str:
    return render_current_flow_file_rows_block(
        source,
        "workflow_file_rows",
        CURRENT_FLOW_WORKFLOW_FILES_START,
        CURRENT_FLOW_WORKFLOW_FILES_END,
    )


def render_current_flow_operator_files_block(source: dict[str, Any]) -> str:
    return render_current_flow_file_rows_block(
        source,
        "operator_file_rows",
        CURRENT_FLOW_OPERATOR_FILES_START,
        CURRENT_FLOW_OPERATOR_FILES_END,
    )


def render_current_flow_literal_block(source: dict[str, Any], key: str, start_marker: str, end_marker: str) -> str:
    items = resolve_section_strings(source, "current_flow", key)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_text_bullets(items),
        end_marker,
    ]
    return "\n".join(lines)


def render_current_flow_persona_stops_block(source: dict[str, Any]) -> str:
    return render_current_flow_literal_block(
        source,
        "persona_stop_items",
        CURRENT_FLOW_PERSONA_STOPS_START,
        CURRENT_FLOW_PERSONA_STOPS_END,
    )


def render_current_flow_pipeline_stops_block(source: dict[str, Any]) -> str:
    return render_current_flow_literal_block(
        source,
        "pipeline_stop_items",
        CURRENT_FLOW_PIPELINE_STOPS_START,
        CURRENT_FLOW_PIPELINE_STOPS_END,
    )


def render_current_flow_runtime_stops_block(source: dict[str, Any]) -> str:
    return render_current_flow_literal_block(
        source,
        "runtime_stop_items",
        CURRENT_FLOW_RUNTIME_STOPS_START,
        CURRENT_FLOW_RUNTIME_STOPS_END,
    )


def render_current_flow_operator_stops_block(source: dict[str, Any]) -> str:
    return render_current_flow_literal_block(
        source,
        "operator_stop_items",
        CURRENT_FLOW_OPERATOR_STOPS_START,
        CURRENT_FLOW_OPERATOR_STOPS_END,
    )


def render_current_flow_described_block(
    source: dict[str, Any], key: str, start_marker: str, end_marker: str
) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "current_flow", key, commands)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        end_marker,
    ]
    return "\n".join(lines)


def render_current_flow_persona_resume_block(source: dict[str, Any]) -> str:
    return render_current_flow_described_block(
        source,
        "persona_resume_items",
        CURRENT_FLOW_PERSONA_RESUME_START,
        CURRENT_FLOW_PERSONA_RESUME_END,
    )


def render_current_flow_pipeline_resume_block(source: dict[str, Any]) -> str:
    return render_current_flow_described_block(
        source,
        "pipeline_resume_items",
        CURRENT_FLOW_PIPELINE_RESUME_START,
        CURRENT_FLOW_PIPELINE_RESUME_END,
    )


def render_current_flow_runtime_resume_block(source: dict[str, Any]) -> str:
    return render_current_flow_described_block(
        source,
        "runtime_resume_items",
        CURRENT_FLOW_RUNTIME_RESUME_START,
        CURRENT_FLOW_RUNTIME_RESUME_END,
    )


def render_current_flow_operator_resume_block(source: dict[str, Any]) -> str:
    return render_current_flow_described_block(
        source,
        "operator_resume_items",
        CURRENT_FLOW_OPERATOR_RESUME_START,
        CURRENT_FLOW_OPERATOR_RESUME_END,
    )


def render_current_flow_operator_route_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_item_specs(source, "current_flow", "operator_chain_items", commands)
    lines = [
        CURRENT_FLOW_OPERATOR_ROUTE_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "文字版：",
        "",
        *render_arrow_surfaces(items),
        "",
        *render_mermaid_chain(items),
        CURRENT_FLOW_OPERATOR_ROUTE_END,
    ]
    return "\n".join(lines)


def render_current_flow_operator_chain_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "current_flow", "operator_chain_items", commands)
    lines = [
        CURRENT_FLOW_OPERATOR_CHAIN_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_described(items),
        CURRENT_FLOW_OPERATOR_CHAIN_END,
    ]
    return "\n".join(lines)


def render_current_flow(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                CURRENT_FLOW_ENTRY_CHOICES_START,
                CURRENT_FLOW_ENTRY_CHOICES_END,
                render_current_flow_entry_choices_block(source),
            ),
            (
                CURRENT_FLOW_EXAMPLES_START,
                CURRENT_FLOW_EXAMPLES_END,
                render_current_flow_examples_block(source),
            ),
            (
                CURRENT_FLOW_OPERATOR_ROUTE_START,
                CURRENT_FLOW_OPERATOR_ROUTE_END,
                render_current_flow_operator_route_block(source),
            ),
            (
                CURRENT_FLOW_OPERATOR_CHAIN_START,
                CURRENT_FLOW_OPERATOR_CHAIN_END,
                render_current_flow_operator_chain_block(source),
            ),
            (
                CURRENT_FLOW_PERSONA_STOPS_START,
                CURRENT_FLOW_PERSONA_STOPS_END,
                render_current_flow_persona_stops_block(source),
            ),
            (
                CURRENT_FLOW_PIPELINE_STOPS_START,
                CURRENT_FLOW_PIPELINE_STOPS_END,
                render_current_flow_pipeline_stops_block(source),
            ),
            (
                CURRENT_FLOW_RUNTIME_STOPS_START,
                CURRENT_FLOW_RUNTIME_STOPS_END,
                render_current_flow_runtime_stops_block(source),
            ),
            (
                CURRENT_FLOW_OPERATOR_STOPS_START,
                CURRENT_FLOW_OPERATOR_STOPS_END,
                render_current_flow_operator_stops_block(source),
            ),
            (
                CURRENT_FLOW_PERSONA_RESUME_START,
                CURRENT_FLOW_PERSONA_RESUME_END,
                render_current_flow_persona_resume_block(source),
            ),
            (
                CURRENT_FLOW_PIPELINE_RESUME_START,
                CURRENT_FLOW_PIPELINE_RESUME_END,
                render_current_flow_pipeline_resume_block(source),
            ),
            (
                CURRENT_FLOW_RUNTIME_RESUME_START,
                CURRENT_FLOW_RUNTIME_RESUME_END,
                render_current_flow_runtime_resume_block(source),
            ),
            (
                CURRENT_FLOW_OPERATOR_RESUME_START,
                CURRENT_FLOW_OPERATOR_RESUME_END,
                render_current_flow_operator_resume_block(source),
            ),
            (
                CURRENT_FLOW_PERSONA_FILES_START,
                CURRENT_FLOW_PERSONA_FILES_END,
                render_current_flow_persona_files_block(source),
            ),
            (
                CURRENT_FLOW_WORKFLOW_FILES_START,
                CURRENT_FLOW_WORKFLOW_FILES_END,
                render_current_flow_workflow_files_block(source),
            ),
            (
                CURRENT_FLOW_OPERATOR_FILES_START,
                CURRENT_FLOW_OPERATOR_FILES_END,
                render_current_flow_operator_files_block(source),
            ),
        ],
    )


def render_capability_index_entry_block(source: dict[str, Any]) -> str:
    items = resolve_section_strings(source, "capability_index", "operator_entry_scripts")
    lines = [
        CAPABILITY_INDEX_ENTRY_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_literal_bullets(items),
        CAPABILITY_INDEX_ENTRY_END,
    ]
    return "\n".join(lines)


def render_capability_index_capabilities_block(source: dict[str, Any]) -> str:
    items = resolve_section_strings(source, "capability_index", "operator_capability_lines")
    lines = [
        CAPABILITY_INDEX_CAPABILITIES_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_text_bullets(items),
        CAPABILITY_INDEX_CAPABILITIES_END,
    ]
    return "\n".join(lines)


def render_capability_index_recent_release_behavior_block(source: dict[str, Any]) -> str:
    items = resolve_section_strings(source, "playbook", "release_behavior_lines")
    lines = [
        CAPABILITY_INDEX_RECENT_RELEASE_BEHAVIOR_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_text_bullets(items),
        CAPABILITY_INDEX_RECENT_RELEASE_BEHAVIOR_END,
    ]
    return "\n".join(lines)


def render_capability_index(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                CAPABILITY_INDEX_ENTRY_START,
                CAPABILITY_INDEX_ENTRY_END,
                render_capability_index_entry_block(source),
            ),
            (
                CAPABILITY_INDEX_CAPABILITIES_START,
                CAPABILITY_INDEX_CAPABILITIES_END,
                render_capability_index_capabilities_block(source),
            ),
            (
                CAPABILITY_INDEX_RECENT_RELEASE_BEHAVIOR_START,
                CAPABILITY_INDEX_RECENT_RELEASE_BEHAVIOR_END,
                render_capability_index_recent_release_behavior_block(source),
            ),
        ],
    )


def render_doc_router_question_table_block(source: dict[str, Any]) -> str:
    rows = resolve_doc_router_rows(source)
    lines = [
        DOC_ROUTER_QUESTION_TABLE_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "| 你现在的问题 | 先看哪份文档 | 为什么 |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['question']} | {render_doc_link(row['path'])} | {row['reason']} |")
    lines.append(DOC_ROUTER_QUESTION_TABLE_END)
    return "\n".join(lines)


def render_doc_router_maintainer_path_block(source: dict[str, Any]) -> str:
    items = resolve_doc_router_paths(source, "maintainer_reading_path")
    lines = [
        DOC_ROUTER_MAINTAINER_PATH_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
    ]
    for idx, item in enumerate(items, start=1):
        lines.append(f"{idx}. {render_doc_link(item)}")
    lines.append(DOC_ROUTER_MAINTAINER_PATH_END)
    return "\n".join(lines)


def render_doc_router_user_value_path_block(source: dict[str, Any]) -> str:
    items = resolve_doc_router_paths(source, "user_value_path")
    lines = [
        DOC_ROUTER_USER_VALUE_PATH_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_doc_links(items),
        DOC_ROUTER_USER_VALUE_PATH_END,
    ]
    return "\n".join(lines)


def render_doc_router_workflow_path_block(source: dict[str, Any]) -> str:
    items = resolve_doc_router_paths(source, "workflow_path")
    lines = [
        DOC_ROUTER_WORKFLOW_PATH_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_doc_links(items),
        DOC_ROUTER_WORKFLOW_PATH_END,
    ]
    return "\n".join(lines)


def render_doc_router_single_read_block(source: dict[str, Any]) -> str:
    items = resolve_doc_router_single_read_items(source)
    lines = [
        DOC_ROUTER_SINGLE_READ_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_single_read_bullets(items),
        DOC_ROUTER_SINGLE_READ_END,
    ]
    return "\n".join(lines)


def render_doc_router(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                DOC_ROUTER_QUESTION_TABLE_START,
                DOC_ROUTER_QUESTION_TABLE_END,
                render_doc_router_question_table_block(source),
            ),
            (
                DOC_ROUTER_USER_VALUE_PATH_START,
                DOC_ROUTER_USER_VALUE_PATH_END,
                render_doc_router_user_value_path_block(source),
            ),
            (
                DOC_ROUTER_WORKFLOW_PATH_START,
                DOC_ROUTER_WORKFLOW_PATH_END,
                render_doc_router_workflow_path_block(source),
            ),
            (
                DOC_ROUTER_SINGLE_READ_START,
                DOC_ROUTER_SINGLE_READ_END,
                render_doc_router_single_read_block(source),
            ),
            (
                DOC_ROUTER_MAINTAINER_PATH_START,
                DOC_ROUTER_MAINTAINER_PATH_END,
                render_doc_router_maintainer_path_block(source),
            ),
        ],
    )


def render_failure_guide_release_commands_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "failure_guide", "release_readiness_command_items", commands)
    lines = [
        FAILURE_GUIDE_RELEASE_COMMANDS_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_command_table(items, "目标", "命令"),
        FAILURE_GUIDE_RELEASE_COMMANDS_END,
    ]
    return "\n".join(lines)


def render_failure_guide_release_inspect_block(source: dict[str, Any]) -> str:
    return render_failure_guide_text_block(
        source,
        "release_readiness_inspect_items",
        FAILURE_GUIDE_RELEASE_INSPECT_START,
        FAILURE_GUIDE_RELEASE_INSPECT_END,
    )


def render_failure_guide_workflow_blocker_commands_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "failure_guide", "workflow_blocker_command_items", commands)
    lines = [
        FAILURE_GUIDE_WORKFLOW_BLOCKER_COMMANDS_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_command_table(items, "场景", "命令"),
        FAILURE_GUIDE_WORKFLOW_BLOCKER_COMMANDS_END,
    ]
    return "\n".join(lines)


def render_failure_guide_blueprint_commands_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "failure_guide", "blueprint_command_items", commands)
    lines = [
        FAILURE_GUIDE_BLUEPRINT_COMMANDS_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_command_table(items, "场景", "命令"),
        FAILURE_GUIDE_BLUEPRINT_COMMANDS_END,
    ]
    return "\n".join(lines)


def render_failure_guide_bullet_commands_block(source: dict[str, Any], key: str, start_marker: str, end_marker: str) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "failure_guide", key, commands)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_bullets(items),
        end_marker,
    ]
    return "\n".join(lines)


def render_failure_guide_text_block(source: dict[str, Any], key: str, start_marker: str, end_marker: str) -> str:
    items = resolve_section_strings(source, "failure_guide", key)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_text_bullets(items),
        end_marker,
    ]
    return "\n".join(lines)


def render_failure_guide_numbered_text_block(
    source: dict[str, Any], key: str, start_marker: str, end_marker: str
) -> str:
    items = resolve_section_strings(source, "failure_guide", key)
    lines = [
        start_marker,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_text(items),
        end_marker,
    ]
    return "\n".join(lines)


def render_failure_guide_personal_empty_commands_block(source: dict[str, Any]) -> str:
    return render_failure_guide_bullet_commands_block(
        source,
        "personal_empty_command_items",
        FAILURE_GUIDE_PERSONAL_EMPTY_COMMANDS_START,
        FAILURE_GUIDE_PERSONAL_EMPTY_COMMANDS_END,
    )


def render_failure_guide_stage_confirmation_commands_block(source: dict[str, Any]) -> str:
    return render_failure_guide_bullet_commands_block(
        source,
        "stage_confirmation_command_items",
        FAILURE_GUIDE_STAGE_CONFIRMATION_COMMANDS_START,
        FAILURE_GUIDE_STAGE_CONFIRMATION_COMMANDS_END,
    )


def render_failure_guide_next_interview_commands_block(source: dict[str, Any]) -> str:
    return render_failure_guide_bullet_commands_block(
        source,
        "next_interview_command_items",
        FAILURE_GUIDE_NEXT_INTERVIEW_COMMANDS_START,
        FAILURE_GUIDE_NEXT_INTERVIEW_COMMANDS_END,
    )


def render_failure_guide_eval_draft_commands_block(source: dict[str, Any]) -> str:
    return render_failure_guide_bullet_commands_block(
        source,
        "eval_draft_command_items",
        FAILURE_GUIDE_EVAL_DRAFT_COMMANDS_START,
        FAILURE_GUIDE_EVAL_DRAFT_COMMANDS_END,
    )


def render_failure_guide_runtime_commands_block(source: dict[str, Any]) -> str:
    return render_failure_guide_bullet_commands_block(
        source,
        "runtime_command_items",
        FAILURE_GUIDE_RUNTIME_COMMANDS_START,
        FAILURE_GUIDE_RUNTIME_COMMANDS_END,
    )


def render_failure_guide_workflow_blocker_steps_block(source: dict[str, Any]) -> str:
    return render_failure_guide_text_block(
        source,
        "workflow_blocker_next_step_items",
        FAILURE_GUIDE_WORKFLOW_BLOCKER_STEPS_START,
        FAILURE_GUIDE_WORKFLOW_BLOCKER_STEPS_END,
    )


def render_failure_guide_stage_confirmation_steps_block(source: dict[str, Any]) -> str:
    return render_failure_guide_text_block(
        source,
        "stage_confirmation_next_step_items",
        FAILURE_GUIDE_STAGE_CONFIRMATION_STEPS_START,
        FAILURE_GUIDE_STAGE_CONFIRMATION_STEPS_END,
    )


def render_failure_guide_release_next_steps_block(source: dict[str, Any]) -> str:
    return render_failure_guide_numbered_text_block(
        source,
        "release_readiness_next_step_items",
        FAILURE_GUIDE_RELEASE_NEXT_STEPS_START,
        FAILURE_GUIDE_RELEASE_NEXT_STEPS_END,
    )


def render_failure_guide_blueprint_inspect_block(source: dict[str, Any]) -> str:
    return render_failure_guide_text_block(
        source,
        "blueprint_inspect_items",
        FAILURE_GUIDE_BLUEPRINT_INSPECT_START,
        FAILURE_GUIDE_BLUEPRINT_INSPECT_END,
    )


def render_failure_guide_latest_stack_inspect_block(source: dict[str, Any]) -> str:
    return render_failure_guide_text_block(
        source,
        "latest_stack_inspect_items",
        FAILURE_GUIDE_LATEST_STACK_INSPECT_START,
        FAILURE_GUIDE_LATEST_STACK_INSPECT_END,
    )


def render_failure_guide_latest_stack_next_steps_block(source: dict[str, Any]) -> str:
    return render_failure_guide_text_block(
        source,
        "latest_stack_next_step_items",
        FAILURE_GUIDE_LATEST_STACK_NEXT_STEPS_START,
        FAILURE_GUIDE_LATEST_STACK_NEXT_STEPS_END,
    )


def render_failure_guide_quick_reference_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    rows = resolve_failure_guide_quick_reference_rows(source, commands)
    lines = [
        FAILURE_GUIDE_QUICK_REFERENCE_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        "| 问题 | 先看什么 | 最快命令 |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['problem']} | {row['inspect']} | `{row['command']}` |")
    lines.append(FAILURE_GUIDE_QUICK_REFERENCE_END)
    return "\n".join(lines)


def render_failure_guide_reading_order_block(source: dict[str, Any]) -> str:
    items = resolve_failure_guide_reading_order_items(source)
    lines = [
        FAILURE_GUIDE_READING_ORDER_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_numbered_doc_steps(items),
        FAILURE_GUIDE_READING_ORDER_END,
    ]
    return "\n".join(lines)


def render_failure_guide_latest_stack_commands_block(source: dict[str, Any]) -> str:
    commands = ensure_command_map(source)
    items = resolve_section_items(source, "failure_guide", "latest_stack_command_items", commands)
    lines = [
        FAILURE_GUIDE_LATEST_STACK_COMMANDS_START,
        "<!-- Generated from references/operator_commands.json via scripts/render_operator_command_docs.py. Do not edit by hand. -->",
        "",
        *render_described_command_table(items, "目标", "命令"),
        FAILURE_GUIDE_LATEST_STACK_COMMANDS_END,
    ]
    return "\n".join(lines)


def render_failure_guide(source: dict[str, Any], text: str) -> str:
    return apply_render_blocks(
        text,
        [
            (
                FAILURE_GUIDE_PERSONAL_EMPTY_INSPECT_START,
                FAILURE_GUIDE_PERSONAL_EMPTY_INSPECT_END,
                render_failure_guide_text_block(
                    source,
                    "personal_empty_inspect_items",
                    FAILURE_GUIDE_PERSONAL_EMPTY_INSPECT_START,
                    FAILURE_GUIDE_PERSONAL_EMPTY_INSPECT_END,
                ),
            ),
            (
                FAILURE_GUIDE_PERSONAL_EMPTY_NEXT_STEPS_START,
                FAILURE_GUIDE_PERSONAL_EMPTY_NEXT_STEPS_END,
                render_failure_guide_text_block(
                    source,
                    "personal_empty_next_step_items",
                    FAILURE_GUIDE_PERSONAL_EMPTY_NEXT_STEPS_START,
                    FAILURE_GUIDE_PERSONAL_EMPTY_NEXT_STEPS_END,
                ),
            ),
            (
                FAILURE_GUIDE_NEXT_INTERVIEW_INSPECT_START,
                FAILURE_GUIDE_NEXT_INTERVIEW_INSPECT_END,
                render_failure_guide_text_block(
                    source,
                    "next_interview_inspect_items",
                    FAILURE_GUIDE_NEXT_INTERVIEW_INSPECT_START,
                    FAILURE_GUIDE_NEXT_INTERVIEW_INSPECT_END,
                ),
            ),
            (
                FAILURE_GUIDE_NEXT_INTERVIEW_NEXT_STEPS_START,
                FAILURE_GUIDE_NEXT_INTERVIEW_NEXT_STEPS_END,
                render_failure_guide_text_block(
                    source,
                    "next_interview_next_step_items",
                    FAILURE_GUIDE_NEXT_INTERVIEW_NEXT_STEPS_START,
                    FAILURE_GUIDE_NEXT_INTERVIEW_NEXT_STEPS_END,
                ),
            ),
            (
                FAILURE_GUIDE_EVAL_DRAFT_INSPECT_START,
                FAILURE_GUIDE_EVAL_DRAFT_INSPECT_END,
                render_failure_guide_text_block(
                    source,
                    "eval_draft_inspect_items",
                    FAILURE_GUIDE_EVAL_DRAFT_INSPECT_START,
                    FAILURE_GUIDE_EVAL_DRAFT_INSPECT_END,
                ),
            ),
            (
                FAILURE_GUIDE_EVAL_DRAFT_NEXT_STEPS_START,
                FAILURE_GUIDE_EVAL_DRAFT_NEXT_STEPS_END,
                render_failure_guide_text_block(
                    source,
                    "eval_draft_next_step_items",
                    FAILURE_GUIDE_EVAL_DRAFT_NEXT_STEPS_START,
                    FAILURE_GUIDE_EVAL_DRAFT_NEXT_STEPS_END,
                ),
            ),
            (
                FAILURE_GUIDE_RELEASE_INSPECT_START,
                FAILURE_GUIDE_RELEASE_INSPECT_END,
                render_failure_guide_release_inspect_block(source),
            ),
            (
                FAILURE_GUIDE_RELEASE_NEXT_STEPS_START,
                FAILURE_GUIDE_RELEASE_NEXT_STEPS_END,
                render_failure_guide_release_next_steps_block(source),
            ),
            (
                FAILURE_GUIDE_WORKFLOW_BLOCKER_INSPECT_START,
                FAILURE_GUIDE_WORKFLOW_BLOCKER_INSPECT_END,
                render_failure_guide_text_block(
                    source,
                    "workflow_blocker_inspect_items",
                    FAILURE_GUIDE_WORKFLOW_BLOCKER_INSPECT_START,
                    FAILURE_GUIDE_WORKFLOW_BLOCKER_INSPECT_END,
                ),
            ),
            (
                FAILURE_GUIDE_WORKFLOW_BLOCKER_COMMANDS_START,
                FAILURE_GUIDE_WORKFLOW_BLOCKER_COMMANDS_END,
                render_failure_guide_workflow_blocker_commands_block(source),
            ),
            (
                FAILURE_GUIDE_BLUEPRINT_COMMANDS_START,
                FAILURE_GUIDE_BLUEPRINT_COMMANDS_END,
                render_failure_guide_blueprint_commands_block(source),
            ),
            (
                FAILURE_GUIDE_PERSONAL_EMPTY_COMMANDS_START,
                FAILURE_GUIDE_PERSONAL_EMPTY_COMMANDS_END,
                render_failure_guide_personal_empty_commands_block(source),
            ),
            (
                FAILURE_GUIDE_WORKFLOW_BLOCKER_STEPS_START,
                FAILURE_GUIDE_WORKFLOW_BLOCKER_STEPS_END,
                render_failure_guide_workflow_blocker_steps_block(source),
            ),
            (
                FAILURE_GUIDE_NEXT_INTERVIEW_COMMANDS_START,
                FAILURE_GUIDE_NEXT_INTERVIEW_COMMANDS_END,
                render_failure_guide_next_interview_commands_block(source),
            ),
            (
                FAILURE_GUIDE_EVAL_DRAFT_COMMANDS_START,
                FAILURE_GUIDE_EVAL_DRAFT_COMMANDS_END,
                render_failure_guide_eval_draft_commands_block(source),
            ),
            (
                FAILURE_GUIDE_STAGE_CONFIRMATION_STEPS_START,
                FAILURE_GUIDE_STAGE_CONFIRMATION_STEPS_END,
                render_failure_guide_stage_confirmation_steps_block(source),
            ),
            (
                FAILURE_GUIDE_STAGE_CONFIRMATION_INSPECT_START,
                FAILURE_GUIDE_STAGE_CONFIRMATION_INSPECT_END,
                render_failure_guide_text_block(
                    source,
                    "stage_confirmation_inspect_items",
                    FAILURE_GUIDE_STAGE_CONFIRMATION_INSPECT_START,
                    FAILURE_GUIDE_STAGE_CONFIRMATION_INSPECT_END,
                ),
            ),
            (
                FAILURE_GUIDE_BLUEPRINT_REASONS_START,
                FAILURE_GUIDE_BLUEPRINT_REASONS_END,
                render_failure_guide_text_block(
                    source,
                    "blueprint_reason_items",
                    FAILURE_GUIDE_BLUEPRINT_REASONS_START,
                    FAILURE_GUIDE_BLUEPRINT_REASONS_END,
                ),
            ),
            (
                FAILURE_GUIDE_BLUEPRINT_INSPECT_START,
                FAILURE_GUIDE_BLUEPRINT_INSPECT_END,
                render_failure_guide_blueprint_inspect_block(source),
            ),
            (
                FAILURE_GUIDE_BLUEPRINT_NEXT_STEPS_START,
                FAILURE_GUIDE_BLUEPRINT_NEXT_STEPS_END,
                render_failure_guide_text_block(
                    source,
                    "blueprint_next_step_items",
                    FAILURE_GUIDE_BLUEPRINT_NEXT_STEPS_START,
                    FAILURE_GUIDE_BLUEPRINT_NEXT_STEPS_END,
                ),
            ),
            (
                FAILURE_GUIDE_STAGE_CONFIRMATION_COMMANDS_START,
                FAILURE_GUIDE_STAGE_CONFIRMATION_COMMANDS_END,
                render_failure_guide_stage_confirmation_commands_block(source),
            ),
            (
                FAILURE_GUIDE_RUNTIME_INSPECT_START,
                FAILURE_GUIDE_RUNTIME_INSPECT_END,
                render_failure_guide_text_block(
                    source,
                    "runtime_inspect_items",
                    FAILURE_GUIDE_RUNTIME_INSPECT_START,
                    FAILURE_GUIDE_RUNTIME_INSPECT_END,
                ),
            ),
            (
                FAILURE_GUIDE_RUNTIME_NEXT_STEPS_START,
                FAILURE_GUIDE_RUNTIME_NEXT_STEPS_END,
                render_failure_guide_text_block(
                    source,
                    "runtime_next_step_items",
                    FAILURE_GUIDE_RUNTIME_NEXT_STEPS_START,
                    FAILURE_GUIDE_RUNTIME_NEXT_STEPS_END,
                ),
            ),
            (
                FAILURE_GUIDE_RUNTIME_COMMANDS_START,
                FAILURE_GUIDE_RUNTIME_COMMANDS_END,
                render_failure_guide_runtime_commands_block(source),
            ),
            (
                FAILURE_GUIDE_LATEST_STACK_INSPECT_START,
                FAILURE_GUIDE_LATEST_STACK_INSPECT_END,
                render_failure_guide_latest_stack_inspect_block(source),
            ),
            (
                FAILURE_GUIDE_LATEST_STACK_NEXT_STEPS_START,
                FAILURE_GUIDE_LATEST_STACK_NEXT_STEPS_END,
                render_failure_guide_latest_stack_next_steps_block(source),
            ),
            (
                FAILURE_GUIDE_QUICK_REFERENCE_START,
                FAILURE_GUIDE_QUICK_REFERENCE_END,
                render_failure_guide_quick_reference_block(source),
            ),
            (
                FAILURE_GUIDE_READING_ORDER_START,
                FAILURE_GUIDE_READING_ORDER_END,
                render_failure_guide_reading_order_block(source),
            ),
            (
                FAILURE_GUIDE_RELEASE_COMMANDS_START,
                FAILURE_GUIDE_RELEASE_COMMANDS_END,
                render_failure_guide_release_commands_block(source),
            ),
            (
                FAILURE_GUIDE_LATEST_STACK_COMMANDS_START,
                FAILURE_GUIDE_LATEST_STACK_COMMANDS_END,
                render_failure_guide_latest_stack_commands_block(source),
            ),
        ],
    )


def replace_marked_block(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise SystemExit(f"expected exactly one marker pair: {start_marker} / {end_marker}")
    pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"unable to replace marker block: {start_marker} / {end_marker}")
    return updated


def apply_render_blocks(text: str, blocks: list[tuple[str, str, str]]) -> str:
    updated = text
    for start_marker, end_marker, replacement in blocks:
        updated = replace_marked_block(updated, start_marker, end_marker, replacement)
    return updated


def render_readme(source: dict[str, Any], readme_text: str) -> str:
    return apply_render_blocks(
        readme_text,
        [
            (
                README_COMMAND_BLOCK_START,
                README_COMMAND_BLOCK_END,
                render_readme_quickstart_block(source),
            ),
            (
                README_COMMAND_COVERAGE_START,
                README_COMMAND_COVERAGE_END,
                render_readme_coverage_block(source),
            ),
        ],
    )


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_path = Path(args.source).resolve()
    contract_output = Path(args.contract_output).resolve()
    summary_output = Path(args.summary_output).resolve()
    readme_output = Path(args.readme_output).resolve()
    playbook_output = Path(args.playbook_output).resolve()
    new_maintainer_output = Path(args.new_maintainer_output).resolve()
    release_checklist_output = Path(args.release_checklist_output).resolve()
    current_flow_output = Path(args.current_flow_output).resolve()
    capability_index_output = Path(args.capability_index_output).resolve()
    doc_router_output = Path(args.doc_router_output).resolve()
    failure_guide_output = Path(args.failure_guide_output).resolve()

    source = load_source(source_path)
    contract = render_contract(source)
    summary = render_summary(source)
    if not readme_output.exists():
        raise SystemExit(f"missing README target: {readme_output}")
    if not playbook_output.exists():
        raise SystemExit(f"missing playbook target: {playbook_output}")
    if not new_maintainer_output.exists():
        raise SystemExit(f"missing new maintainer target: {new_maintainer_output}")
    if not release_checklist_output.exists():
        raise SystemExit(f"missing release checklist target: {release_checklist_output}")
    if not current_flow_output.exists():
        raise SystemExit(f"missing current flow target: {current_flow_output}")
    if not capability_index_output.exists():
        raise SystemExit(f"missing capability index target: {capability_index_output}")
    if not doc_router_output.exists():
        raise SystemExit(f"missing doc router target: {doc_router_output}")
    if not failure_guide_output.exists():
        raise SystemExit(f"missing failure guide target: {failure_guide_output}")
    readme = render_readme(source, readme_output.read_text(encoding="utf-8"))
    playbook = render_operator_playbook(source, playbook_output.read_text(encoding="utf-8"))
    new_maintainer = render_new_maintainer(source, new_maintainer_output.read_text(encoding="utf-8"))
    release_checklist = render_release_checklist(source, release_checklist_output.read_text(encoding="utf-8"))
    current_flow = render_current_flow(source, current_flow_output.read_text(encoding="utf-8"))
    capability_index = render_capability_index(source, capability_index_output.read_text(encoding="utf-8"))
    doc_router = render_doc_router(source, doc_router_output.read_text(encoding="utf-8"))
    failure_guide = render_failure_guide(source, failure_guide_output.read_text(encoding="utf-8"))

    if args.check:
        failures: list[str] = []
        if not contract_output.exists() or contract_output.read_text(encoding="utf-8") != contract:
            failures.append(str(contract_output))
        if not summary_output.exists() or summary_output.read_text(encoding="utf-8") != summary:
            failures.append(str(summary_output))
        if readme_output.read_text(encoding="utf-8") != readme:
            failures.append(str(readme_output))
        if playbook_output.read_text(encoding="utf-8") != playbook:
            failures.append(str(playbook_output))
        if new_maintainer_output.read_text(encoding="utf-8") != new_maintainer:
            failures.append(str(new_maintainer_output))
        if release_checklist_output.read_text(encoding="utf-8") != release_checklist:
            failures.append(str(release_checklist_output))
        if current_flow_output.read_text(encoding="utf-8") != current_flow:
            failures.append(str(current_flow_output))
        if capability_index_output.read_text(encoding="utf-8") != capability_index:
            failures.append(str(capability_index_output))
        if doc_router_output.read_text(encoding="utf-8") != doc_router:
            failures.append(str(doc_router_output))
        if failure_guide_output.read_text(encoding="utf-8") != failure_guide:
            failures.append(str(failure_guide_output))
        if failures:
            raise SystemExit("render drift: " + ", ".join(failures))
        return 0

    write_if_changed(contract_output, contract)
    write_if_changed(summary_output, summary)
    write_if_changed(readme_output, readme)
    write_if_changed(playbook_output, playbook)
    write_if_changed(new_maintainer_output, new_maintainer)
    write_if_changed(release_checklist_output, release_checklist)
    write_if_changed(current_flow_output, current_flow)
    write_if_changed(capability_index_output, capability_index)
    write_if_changed(doc_router_output, doc_router)
    write_if_changed(failure_guide_output, failure_guide)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
