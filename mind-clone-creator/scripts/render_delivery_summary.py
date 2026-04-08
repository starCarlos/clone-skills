#!/usr/bin/env python3
"""Render user-facing delivery summary from clone_config.yaml."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from workflow_target_utils import infer_workflow_target_defined
except ModuleNotFoundError:
    from scripts.workflow_target_utils import infer_workflow_target_defined


def parse_scalar(text: str) -> Any:
    if text == "null":
        return None
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if text in ("true", "false"):
        return text == "true"
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [parse_scalar(part.strip()) for part in inner.split(",")]
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if text.isdigit():
        return int(text)
    return text


def load_simple_yaml(path: Path) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            item_text = line[2:].strip()
            if isinstance(parent, list):
                if ":" in item_text:
                    key, rest = item_text.split(":", 1)
                    item = {key.strip(): parse_scalar(rest.strip())}
                    parent.append(item)
                    stack.append((indent, item))
                else:
                    parent.append(parse_scalar(item_text))
            continue

        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()

        if rest == "|":
            block_lines = []
            while i < len(lines):
                nxt = lines[i]
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt.strip() and nxt_indent <= indent:
                    break
                i += 1
                if nxt.strip():
                    block_lines.append(nxt[indent + 2 :])
            if isinstance(parent, dict):
                parent[key] = "\n".join(block_lines)
            continue

        if rest == "":
            next_nonempty = None
            for j in range(i, len(lines)):
                probe = lines[j]
                if probe.strip() and not probe.lstrip().startswith("#"):
                    next_nonempty = probe
                    break
            if next_nonempty is not None:
                next_indent = len(next_nonempty) - len(next_nonempty.lstrip(" "))
                next_line = next_nonempty.strip()
                container: Any = [] if next_indent > indent and next_line.startswith("- ") else {}
            else:
                container = {}
            if isinstance(parent, dict):
                parent[key] = container
            stack.append((indent, container))
            continue

        if isinstance(parent, dict):
            parent[key] = parse_scalar(rest)
    return root


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


CHECK_HINTS = {
    "mind_profile.work_process.start": "补一个真实任务的起手动作，写清楚你通常先做什么。",
    "mind_profile.work_process.breakdown": "补一个真实任务的拆解路径，写清楚你怎么拆问题和推进。",
    "identity.summary": "补一句更明确的身份定位：你是谁、主要解决什么问题。",
    "identity.expertise": "补 1-3 项最能代表你的核心专长。",
    "identity.boundaries": "补至少 1 条明确边界，说明什么问题你不会直接接。",
    "mind_profile.core_beliefs": "补 3 条核心信念，最好每条配一个真实例子。",
    "expression.language_style": "补一段更接近日常说话方式的原始表达。",
    "runtime.use_this_clone_when": "补这个分身适合出场的场景描述。",
    "runtime.do_not_use_this_clone_when": "补这个分身不该出场的场景描述。",
}


def detect_working_bundle_manifest(clone_config_path: Path) -> Path | None:
    candidates = [
        clone_config_path.parent / "working_clone_bundle_manifest.json",
        clone_config_path.parent.parent / "working_clone_bundle_manifest.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def describe_workflow_state(workflow_enabled: bool, workflow_target_ready: bool, steps: dict[str, Any]) -> str:
    if not workflow_enabled:
        return "未启用 workflow 轨道"
    if not workflow_target_ready:
        return "已开启 workflow 轨道，等待确认第一类典型工作"
    if bool(steps.get("workflow_runtime_bundle", False)):
        return "workflow runtime 已就绪，可继续执行任务回合"
    if bool(steps.get("workflow_clone_skill", False)):
        return "workflow clone skill 已生成，等待或可继续初始化 runtime"
    if bool(steps.get("workflow_pipeline", False)):
        return "workflow blueprint 已生成，等待 workflow clone/runtime"
    return "workflow 轨道已开启，等待继续编译"


def build_workflow_summary(manifest_path: Path | None) -> dict[str, Any] | None:
    if manifest_path is None or not manifest_path.exists():
        return None
    manifest = load_json(manifest_path)
    steps = manifest.get("steps", {}) if isinstance(manifest.get("steps", {}), dict) else {}
    bundle_validation_path = Path(str(manifest.get("bundle_validation_path", "")).strip())
    if bundle_validation_path.exists():
        bundle_validation = load_json(bundle_validation_path)
    else:
        bundle_validation = manifest.get("bundle_validation", {}) if isinstance(manifest.get("bundle_validation", {}), dict) else {}
    workflow_enabled = bool(steps.get("workflow_enabled", False))
    if not workflow_enabled:
        return None
    workflow_target_ready = infer_workflow_target_defined(manifest, steps)
    blockers = bundle_validation.get("blockers", []) if isinstance(bundle_validation.get("blockers", []), list) else []
    blocker_lines = [
        f"{str(item.get('item', '')).strip()}：{str(item.get('reason', '')).strip()}"
        for item in blockers
        if isinstance(item, dict) and str(item.get("item", "")).strip()
    ]
    recommended_next = (
        manifest.get("recommended_next_command", {})
        if isinstance(manifest.get("recommended_next_command", {}), dict)
        else {}
    )
    return {
        "manifest_path": str(manifest_path),
        "target_mode": str(manifest.get("target_mode", "")).strip() or "persona-only",
        "workflow_name": str(manifest.get("workflow_name", "")).strip(),
        "work_unit": str(manifest.get("work_unit", "")).strip(),
        "workflow_enabled": workflow_enabled,
        "workflow_target_defined": workflow_target_ready,
        "bundle_recommended_release": str(bundle_validation.get("recommended_release", "draft")).strip() or "draft",
        "bundle_final_ready": bool(bundle_validation.get("final_ready", False)),
        "workflow_state": describe_workflow_state(workflow_enabled, workflow_target_ready, steps),
        "workflow_interview": str(manifest.get("workflow_interview", "")).strip(),
        "workflow_pipeline_ready": bool(steps.get("workflow_pipeline", False)),
        "workflow_clone_skill_ready": bool(steps.get("workflow_clone_skill", False)),
        "workflow_runtime_bundle_ready": bool(steps.get("workflow_runtime_bundle", False)),
        "blockers": blocker_lines,
        "next_reason": str(recommended_next.get("reason", "")).strip(),
        "next_command": str(recommended_next.get("command", "")).strip(),
        "next_input_source": str(recommended_next.get("input_source", "")).strip(),
    }


def build_summary(config: dict[str, Any], workflow: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = config.get("meta", {})
    readiness = config.get("release_readiness", {})
    persona_draft_status = str(meta.get("draft_status", "draft")).strip() or "draft"
    quality_score = int(meta.get("quality_score", 0))
    clone_name = str(meta.get("name", "个人分身")).strip() or "个人分身"
    failed_checks = readiness.get("failed_checks", [])
    if not isinstance(failed_checks, list):
        failed_checks = []

    missing_actions = []
    for item in failed_checks:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        detail = str(item.get("detail", "")).strip()
        missing_actions.append(
            {
                "name": name,
                "detail": detail,
                "action": CHECK_HINTS.get(name, "补齐这一项对应的信息后再重新生成。"),
            }
        )

    overall_status = persona_draft_status
    if isinstance(workflow, dict):
        overall_status = str(workflow.get("bundle_recommended_release", overall_status)).strip() or overall_status

    if isinstance(workflow, dict) and overall_status != "final" and persona_draft_status == "final":
        headline = f"{clone_name} 的人格层已达到 final 标准，但整体 working bundle 仍是 draft。"
        usage_note = "人格层可以直接使用；如果你要的是工作型替身，还需要按 workflow 区块里的 blocker 继续补齐。"
    elif overall_status == "final":
        headline = f"{clone_name} 已达到 final 标准，可直接使用。"
        usage_note = "建议直接放入 OpenClaw 使用；后续如果你的工作方式有明显变化，再补料重建。"
    else:
        headline = f"{clone_name} 当前仍是 draft，但文件已交付，可先内部使用。"
        usage_note = "适合先做内部试用、风格模拟、低到中风险问题讨论；不建议直接代表本人做高风险判断。"

    return {
        "clone_name": clone_name,
        "draft_status": overall_status,
        "persona_draft_status": persona_draft_status,
        "quality_score": quality_score,
        "headline": headline,
        "usage_note": usage_note,
        "missing_actions": missing_actions,
        "workflow": workflow,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['clone_name']} 交付说明",
        "",
        summary["headline"],
        "",
        f"- 当前状态：`{summary['draft_status']}`",
        f"- 人格层状态：`{summary['persona_draft_status']}`",
        f"- 质量评分：`{summary['quality_score']}/100`",
        f"- 使用建议：{summary['usage_note']}",
    ]
    missing_actions = summary.get("missing_actions", [])
    workflow = summary.get("workflow")
    if missing_actions:
        lines.extend(["", "## 还差什么"])
        for item in missing_actions:
            lines.append(f"- {item['detail']}")
        lines.extend(["", "## 下一步建议"])
        for item in missing_actions:
            lines.append(f"- {item['action']}")
    if isinstance(workflow, dict):
        blockers = workflow.get("blockers", [])
        lines.extend(
            [
                "",
                "## Workflow 状态",
                f"- 目标模式：`{workflow.get('target_mode', 'persona-only')}`",
                f"- working bundle 状态：`{workflow.get('bundle_recommended_release', 'draft')}`",
                f"- 当前阶段：{workflow.get('workflow_state', '未启用 workflow 轨道')}",
                f"- workflow 名称：{workflow.get('workflow_name', '未命名') or '未命名'}",
                f"- 目标工作：`{workflow.get('work_unit', '') or '待确认'}`",
                f"- workflow interview：{workflow.get('workflow_interview', '无') or '无'}",
                f"- workflow pipeline：`{'ready' if workflow.get('workflow_pipeline_ready', False) else 'pending'}`",
                f"- workflow clone skill：`{'ready' if workflow.get('workflow_clone_skill_ready', False) else 'pending'}`",
                f"- workflow runtime：`{'ready' if workflow.get('workflow_runtime_bundle_ready', False) else 'pending'}`",
                f"- 当前 blocker：{'；'.join(blockers) if blockers else '无'}",
                f"- 下一步：{workflow.get('next_reason', '无') or '无'}",
            ]
        )
        next_input = str(workflow.get("next_input_source", "")).strip()
        if next_input:
            lines.append(f"- 先编辑 / 输入：{next_input}")
        next_command = str(workflow.get("next_command", "")).strip()
        if next_command:
            lines.extend(["", "```bash", next_command, "```"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render user-facing delivery summary.")
    parser.add_argument("--input", required=True, help="Path to clone_config.yaml")
    parser.add_argument("--working-bundle-manifest", help="Optional working_clone_bundle_manifest.json path")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).resolve()
    config = load_simple_yaml(input_path)
    manifest_path = Path(args.working_bundle_manifest).resolve() if args.working_bundle_manifest else detect_working_bundle_manifest(input_path)
    summary = build_summary(config, build_workflow_summary(manifest_path))
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
