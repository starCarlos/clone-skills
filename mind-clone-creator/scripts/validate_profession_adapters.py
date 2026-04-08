#!/usr/bin/env python3
"""Validate profession adapter files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def is_command_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, list) and item and all(isinstance(part, str) and part.strip() for part in item)
        for item in value
    )


def normalize_profession_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.strip().lower())


def add_error(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def validate_stage_overrides(value: Any, errors: list[str], path: str) -> None:
    if not isinstance(value, dict):
        add_error(errors, path, "must be an object")
        return
    for stage_name, stage_config in value.items():
        stage_path = f"{path}.{stage_name}"
        if not isinstance(stage_name, str) or not stage_name.strip():
            add_error(errors, stage_path, "stage name must be a non-empty string")
            continue
        if not isinstance(stage_config, dict):
            add_error(errors, stage_path, "stage config must be an object")
            continue
        for field in ("preferred_tools", "extra_read", "extra_produce", "notes"):
            if field in stage_config and not is_string_list(stage_config[field]):
                add_error(errors, f"{stage_path}.{field}", "must be a non-empty string list")


def validate_execution_overrides(value: Any, errors: list[str], path: str, templates_dir: Path) -> None:
    if not isinstance(value, dict):
        add_error(errors, path, "must be an object")
        return

    tool_preferences = value.get("tool_preferences")
    if tool_preferences is not None:
        if not isinstance(tool_preferences, dict):
            add_error(errors, f"{path}.tool_preferences", "must be an object")
        else:
            for tool_name, override in tool_preferences.items():
                tool_path = f"{path}.tool_preferences.{tool_name}"
                if not isinstance(tool_name, str) or not tool_name.strip():
                    add_error(errors, tool_path, "tool key must be a non-empty string")
                    continue
                if not isinstance(override, dict):
                    add_error(errors, tool_path, "override must be an object")
                    continue
                if "prefer_mode" in override and not isinstance(override["prefer_mode"], str):
                    add_error(errors, f"{tool_path}.prefer_mode", "must be a string")
                if "retry_fallback_candidates" in override and not isinstance(override["retry_fallback_candidates"], bool):
                    add_error(errors, f"{tool_path}.retry_fallback_candidates", "must be a boolean")
                if "prefer_collect_artifacts" in override and not is_string_list(override["prefer_collect_artifacts"]):
                    add_error(errors, f"{tool_path}.prefer_collect_artifacts", "must be a non-empty string list")

    artifact_templates = value.get("artifact_templates")
    if artifact_templates is not None:
        if not isinstance(artifact_templates, dict):
            add_error(errors, f"{path}.artifact_templates", "must be an object")
        else:
            for tool_name, template_name in artifact_templates.items():
                template_path = f"{path}.artifact_templates.{tool_name}"
                if not isinstance(tool_name, str) or not tool_name.strip():
                    add_error(errors, template_path, "tool key must be a non-empty string")
                    continue
                if not isinstance(template_name, str) or not template_name.strip():
                    add_error(errors, template_path, "template must be a non-empty string")
                    continue
                if not (templates_dir / template_name).exists():
                    add_error(errors, template_path, f"template not found: {template_name}")


def validate_adapter(path: Path, templates_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"file": str(path), "valid": False, "errors": [f"json_parse: {exc}"], "warnings": warnings}

    if not isinstance(data, dict):
        return {"file": str(path), "valid": False, "errors": ["root: must be a JSON object"], "warnings": warnings}

    if not is_string_list(data.get("profession_aliases")):
        add_error(errors, "profession_aliases", "must be a non-empty string list")

    if "preferred_repo_types" in data and not is_string_list(data["preferred_repo_types"]):
        add_error(errors, "preferred_repo_types", "must be a non-empty string list")
    if "preferred_test_commands" in data and not is_command_list(data["preferred_test_commands"]):
        add_error(errors, "preferred_test_commands", "must be a list of non-empty string lists")
    if "preferred_run_commands" in data and not is_command_list(data["preferred_run_commands"]):
        add_error(errors, "preferred_run_commands", "must be a list of non-empty string lists")
    if "notes" in data and not is_string_list(data["notes"]):
        add_error(errors, "notes", "must be a non-empty string list")

    if "stage_overrides" in data:
        validate_stage_overrides(data["stage_overrides"], errors, "stage_overrides")
    if "execution_overrides" in data:
        validate_execution_overrides(data["execution_overrides"], errors, "execution_overrides", templates_dir)

    if "profession_aliases" in data and isinstance(data["profession_aliases"], list):
        normalized = [str(item).strip().lower() for item in data["profession_aliases"] if str(item).strip()]
        if len(normalized) != len(set(normalized)):
            warnings.append("profession_aliases: contains duplicates after case-folding")
        normalized_keys = [normalize_profession_key(str(item)) for item in data["profession_aliases"] if str(item).strip()]
        normalized_keys = [item for item in normalized_keys if item]
        if len(normalized_keys) != len(set(normalized_keys)):
            warnings.append("profession_aliases: contains duplicates after normalized matching")

    return {
        "file": str(path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate profession adapters.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    adapters_dir = workspace / "references" / "profession-adapters"
    templates_dir = workspace / "templates"
    results = []
    if adapters_dir.exists():
        for path in sorted(adapters_dir.glob("*.json")):
            results.append(validate_adapter(path, templates_dir))
    summary = {
        "valid": all(item.get("valid", False) for item in results) if results else True,
        "adapter_count": len(results),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
