#!/usr/bin/env python3
"""Assemble a draft clone_config.yaml from structured JSON input."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from validate_clone_config import validate as validate_release_readiness


UTC_PLUS_8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(UTC_PLUS_8).isoformat(timespec="seconds")


def default_config(timestamp: str) -> dict[str, Any]:
    return {
        "meta": {
            "name": "",
            "creator": "",
            "profession": "",
            "platform_target": "openclaw",
            "created_at": timestamp,
            "last_updated_at": timestamp,
            "source_mode": "self_interview",
            "draft_status": "draft",
            "version": "1.0",
            "quality_score": 0,
            "clone_type": "self",
            "identity_confirmed": True,
        },
        "identity": {
            "summary": "",
            "expertise": [],
            "boundaries": [],
        },
        "mind_profile": {
            "core_beliefs": [],
            "thinking_style": "",
            "frameworks": [],
            "blind_spots": [],
            "decision_style": "",
            "priority_order": "",
        },
        "expression": {
            "language_style": "",
            "response_format": "",
            "avoid": [],
        },
        "runtime": {
            "activation_mode": "always_on",
            "exit_commands": ["退出分身模式", "我要和真正的AI说话"],
            "use_this_clone_when": [],
            "do_not_use_this_clone_when": [],
            "memory": {
                "remember": [
                    "用户的核心问题和背景",
                    "已经给出的建议，保持一致性",
                    "用户对回答的反馈",
                ],
                "forget": [
                    "用户的私人信息（除非用户主动要求）",
                    "超出能力边界的承诺",
                ],
            },
        },
        "skills": {
            "universal": {
                "web_search": {"enabled": False, "use_case": ""},
                "code_execution": {"enabled": False, "languages": []},
                "data_analysis": {"enabled": False, "formats": []},
                "file_handling": {"enabled": False, "types": []},
            },
            "professional": [],
        },
        "knowledge_base": {
            "sources": [],
        },
        "source_materials": [],
        "confidence_by_dimension": {
            "identity": 0,
            "capability_boundary": 0,
            "thinking_style": 0,
            "values": 0,
            "expression_style": 0,
        },
        "evidence_map": {
            "summary": [],
            "core_beliefs": [],
            "boundaries": [],
        },
        "system_prompt": "",
        "eval_summary": {
            "overall_score": 0,
            "consistency": 0,
            "thinking_restoration": 0,
            "language_style": 0,
            "boundary_awareness": 0,
            "reasoning": 0,
            "consistency_track": 0,
            "transfer_track": 0,
            "top_improvement": "",
        },
        "update_log": [
            {
                "date": timestamp,
                "change": "Initial creation",
                "reason": "Created from structured self-interview",
            }
        ],
    }


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON must be an object at the top level.")
    return data


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump_yaml(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, str) and "\n" in item:
                lines.append(f"{prefix}{key}: |")
                for part in item.splitlines():
                    lines.append(f"{prefix}  {part}")
            elif isinstance(item, dict):
                lines.append(f"{prefix}{key}:")
                lines.extend(dump_yaml(item, indent + 2))
            elif isinstance(item, list):
                if not item:
                    lines.append(f"{prefix}{key}: []")
                elif all(not isinstance(elem, (dict, list)) for elem in item):
                    lines.append(f"{prefix}{key}:")
                    for elem in item:
                        lines.append(f"{prefix}  - {yaml_scalar(elem)}")
                else:
                    lines.append(f"{prefix}{key}:")
                    for elem in item:
                        if isinstance(elem, dict):
                            first = True
                            for subkey, subval in elem.items():
                                marker = "- " if first else "  "
                                if isinstance(subval, str) and "\n" in subval:
                                    lines.append(f"{prefix}  {marker}{subkey}: |")
                                    for part in subval.splitlines():
                                        lines.append(f"{prefix}      {part}")
                                elif isinstance(subval, (dict, list)):
                                    lines.append(f"{prefix}  {marker}{subkey}:")
                                    lines.extend(dump_yaml(subval, indent + 4))
                                else:
                                    lines.append(
                                        f"{prefix}  {marker}{subkey}: {yaml_scalar(subval)}"
                                    )
                                first = False
                        elif isinstance(elem, list):
                            lines.append(f"{prefix}  -")
                            lines.extend(dump_yaml(elem, indent + 4))
                        else:
                            lines.append(f"{prefix}  - {yaml_scalar(elem)}")
            else:
                lines.append(f"{prefix}{key}: {yaml_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{prefix}[]"]
        return [f"{prefix}- {yaml_scalar(item)}" for item in value]
    return [f"{prefix}{yaml_scalar(value)}"]


def finalize(config: dict[str, Any], timestamp: str) -> dict[str, Any]:
    meta = config.setdefault("meta", {})
    if not meta.get("created_at"):
        meta["created_at"] = timestamp
    meta["last_updated_at"] = timestamp
    if not meta.get("platform_target"):
        meta["platform_target"] = "openclaw"
    if not meta.get("source_mode"):
        meta["source_mode"] = "self_interview"
    if "identity_confirmed" not in meta:
        meta["identity_confirmed"] = True

    eval_summary = config.setdefault("eval_summary", {})
    if not eval_summary.get("overall_score"):
        eval_summary["overall_score"] = meta.get("quality_score", 0)
    if not meta.get("quality_score"):
        meta["quality_score"] = eval_summary.get("overall_score", 0)

    runtime = config.setdefault("runtime", {})
    if not runtime.get("activation_mode"):
        runtime["activation_mode"] = "always_on"
    if not runtime.get("exit_commands"):
        runtime["exit_commands"] = ["退出分身模式", "我要和真正的AI说话"]
    if not runtime.get("use_this_clone_when"):
        expertise = config.get("identity", {}).get("expertise", [])
        profession = meta.get("profession", "")
        if expertise:
            runtime["use_this_clone_when"] = [
                f"用户咨询 {profession or '相关领域'} 相关问题",
                f"用户需要 {'、'.join(expertise[:3])} 方向的建议",
            ]
        else:
            runtime["use_this_clone_when"] = [f"用户咨询 {profession or '相关领域'} 相关问题"]
    if not runtime.get("do_not_use_this_clone_when"):
        runtime["do_not_use_this_clone_when"] = [
            "用户明确说“退出分身模式”或“我要和真正的AI说话”",
            "用户询问分身对应真人的私人信息或实时动态",
        ]
    memory = runtime.setdefault("memory", {})
    if not memory.get("remember"):
        memory["remember"] = [
            "用户的核心问题和背景",
            "已经给出的建议，保持一致性",
            "用户对回答的反馈",
        ]
    if not memory.get("forget"):
        memory["forget"] = [
            "用户的私人信息（除非用户主动要求）",
            "超出能力边界的承诺",
        ]

    if not config.get("update_log"):
        config["update_log"] = [
            {
                "date": timestamp,
                "change": "Initial creation",
                "reason": "Created from structured self-interview",
            }
        ]

    validation_report = validate_release_readiness(config)
    meta["draft_status"] = validation_report["recommended_draft_status"]
    config["release_readiness"] = {
        "final_ready": validation_report["final_ready"],
        "recommended_draft_status": validation_report["recommended_draft_status"],
        "failed_checks": [
            {
                "name": item["name"],
                "detail": item["detail"],
            }
            for item in validation_report["failed_checks"]
        ],
    }
    return config


def render_document(config: dict[str, Any], timestamp: str) -> str:
    lines = [
        "# mind-clone 分身配置文件",
        "# version: 1.0",
        f"# generated_at: {timestamp}",
        "# schema: clone_config_v1",
        "",
    ]
    lines.extend(dump_yaml(config))
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a draft clone_config.yaml from structured JSON input."
    )
    parser.add_argument("--input", required=True, help="Path to JSON input file.")
    parser.add_argument("--output", required=True, help="Path to YAML output file.")
    parser.add_argument(
        "--timestamp",
        help="Override generated timestamp in ISO-8601 format.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    timestamp = args.timestamp or now_iso()

    source = load_json(input_path)
    config = deep_merge(default_config(timestamp), deepcopy(source))
    config = finalize(config, timestamp)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_document(config, timestamp), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
