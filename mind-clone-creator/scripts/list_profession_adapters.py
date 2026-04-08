#!/usr/bin/env python3
"""List available profession adapters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def compact_nonempty(items: list[Any]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def build_stage_summary(stage_overrides: dict[str, Any]) -> tuple[list[str], list[str]]:
    stage_names = []
    preferred_tools = []
    if not isinstance(stage_overrides, dict):
        return stage_names, preferred_tools
    for stage_name, stage_config in stage_overrides.items():
        if str(stage_name).strip():
            stage_names.append(str(stage_name).strip())
        if isinstance(stage_config, dict):
            preferred_tools.extend(stage_config.get("preferred_tools", []))
    return compact_nonempty(stage_names), compact_nonempty(preferred_tools)


def build_execution_summary(execution_overrides: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(execution_overrides, dict):
        return {
            "tool_preference_targets": [],
            "artifact_template_targets": [],
            "artifact_template_values": [],
        }
    tool_preferences = execution_overrides.get("tool_preferences", {})
    artifact_templates = execution_overrides.get("artifact_templates", {})
    return {
        "tool_preference_targets": compact_nonempty(list(tool_preferences.keys())) if isinstance(tool_preferences, dict) else [],
        "artifact_template_targets": compact_nonempty(list(artifact_templates.keys())) if isinstance(artifact_templates, dict) else [],
        "artifact_template_values": compact_nonempty(list(artifact_templates.values())) if isinstance(artifact_templates, dict) else [],
    }


def build_summary(data: dict[str, Any]) -> dict[str, Any]:
    aliases = data.get("profession_aliases", []) if isinstance(data.get("profession_aliases", []), list) else []
    stage_names, preferred_tools = build_stage_summary(data.get("stage_overrides", {}))
    execution_summary = build_execution_summary(data.get("execution_overrides", {}))
    return {
        "primary_name": str(aliases[0]).strip() if aliases else "",
        "alias_count": len(aliases),
        "aliases": aliases,
        "notes": data.get("notes", []),
        "stage_count": len(stage_names),
        "stage_names": stage_names,
        "preferred_tools": preferred_tools,
        "preferred_repo_types": data.get("preferred_repo_types", []),
        "preferred_test_commands": data.get("preferred_test_commands", []),
        "preferred_run_commands": data.get("preferred_run_commands", []),
        "execution": execution_summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List available profession adapters.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    adapters_dir = workspace / "references" / "profession-adapters"
    adapters = []
    if adapters_dir.exists():
        for path in sorted(adapters_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            stage_overrides = data.get("stage_overrides", {})
            execution_overrides = data.get("execution_overrides", {})
            adapters.append(
                {
                    "file": str(path),
                    "profession_aliases": data.get("profession_aliases", []),
                    "notes": data.get("notes", []),
                    "stage_override_stages": list(stage_overrides.keys()) if isinstance(stage_overrides, dict) else [],
                    "execution_override_keys": list(execution_overrides.keys()) if isinstance(execution_overrides, dict) else [],
                    "summary": build_summary(data),
                }
            )
    Path(args.output).write_text(json.dumps({"adapters": adapters}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
