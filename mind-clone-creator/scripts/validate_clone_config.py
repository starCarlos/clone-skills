#!/usr/bin/env python3
"""Validate clone_config.yaml for draft/final release readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)


def any_enabled_universal_skill(skills: Any) -> bool:
    if not isinstance(skills, dict):
        return False
    universal = skills.get("universal", {})
    if not isinstance(universal, dict):
        return False
    for detail in universal.values():
        if isinstance(detail, dict) and detail.get("enabled") is True:
            return True
    return False


def all_positive_confidence(confidence: Any) -> bool:
    if not isinstance(confidence, dict) or not confidence:
        return False
    values = []
    for value in confidence.values():
        if not isinstance(value, (int, float)):
            return False
        values.append(value)
    return bool(values) and all(value > 0 for value in values)


def validate(config: dict[str, Any]) -> dict[str, Any]:
    meta = config.get("meta", {})
    identity = config.get("identity", {})
    mind_profile = config.get("mind_profile", {})
    expression = config.get("expression", {})
    runtime = config.get("runtime", {})
    skills = config.get("skills", {})
    knowledge_base = config.get("knowledge_base", {})
    confidence_by_dimension = config.get("confidence_by_dimension", {})
    eval_summary = config.get("eval_summary", {})
    evidence_map = config.get("evidence_map", {})

    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add_check("meta.name", bool(str(meta.get("name", "")).strip()), "分身名称必须存在")
    add_check("meta.profession", bool(str(meta.get("profession", "")).strip()), "职业字段必须存在")
    add_check("meta.platform_target", meta.get("platform_target") == "openclaw", "当前只允许输出到 openclaw")
    add_check("meta.identity_confirmed", meta.get("identity_confirmed") is True, "必须确认是本人创建本人分身")

    add_check("identity.summary", bool(str(identity.get("summary", "")).strip()), "身份定位必须存在")
    add_check("identity.expertise", nonempty_list(identity.get("expertise")), "必须至少有一项明确专长")
    add_check("identity.boundaries", nonempty_list(identity.get("boundaries")), "必须至少有一项明确边界")

    add_check("mind_profile.core_beliefs", nonempty_list(mind_profile.get("core_beliefs")), "必须有核心信念")
    add_check("mind_profile.thinking_style", bool(str(mind_profile.get("thinking_style", "")).strip()), "必须有思维方式描述")
    add_check("mind_profile.frameworks", nonempty_list(mind_profile.get("frameworks")), "必须有常用框架")
    add_check("mind_profile.work_process.start", bool(str(mind_profile.get("work_process", {}).get("start", "")).strip()), "必须有工作流程起手动作")
    add_check("mind_profile.work_process.breakdown", bool(str(mind_profile.get("work_process", {}).get("breakdown", "")).strip()), "必须有工作流程拆解路径")

    add_check("expression.language_style", bool(str(expression.get("language_style", "")).strip()), "必须有表达风格")
    add_check("expression.response_format", bool(str(expression.get("response_format", "")).strip()), "必须有回答结构偏好")

    add_check("runtime.use_this_clone_when", nonempty_list(runtime.get("use_this_clone_when")), "必须有使用场景")
    add_check("runtime.do_not_use_this_clone_when", nonempty_list(runtime.get("do_not_use_this_clone_when")), "必须有禁用场景")
    add_check("runtime.memory.remember", nonempty_list(runtime.get("memory", {}).get("remember")), "必须有记忆规则")
    add_check("runtime.memory.forget", nonempty_list(runtime.get("memory", {}).get("forget")), "必须有不记忆规则")

    add_check("skills.universal", any_enabled_universal_skill(skills), "至少要有一项启用的通用能力")
    add_check("skills.professional", nonempty_list(skills.get("professional")), "至少要有一项明确专业能力")
    add_check("knowledge_base.sources", nonempty_list(knowledge_base.get("sources")), "技能/知识层必须有可用知识来源或材料类型")
    add_check(
        "confidence_by_dimension",
        all_positive_confidence(confidence_by_dimension),
        "关键维度必须有大于 0 的置信度，不能全部留空或为 0",
    )

    add_check("system_prompt", bool(str(config.get("system_prompt", "")).strip()), "必须有 system_prompt")
    add_check("eval_summary.overall_score", int(eval_summary.get("overall_score", 0)) >= 60, "总分达到 60 才能 final")
    add_check("eval_summary.consistency_track", int(eval_summary.get("consistency_track", 0)) > 0, "必须有访谈一致性轨道分数")
    add_check("eval_summary.transfer_track", int(eval_summary.get("transfer_track", 0)) > 0, "必须有新场景迁移轨道分数")
    add_check("evidence.summary", nonempty_list(evidence_map.get("summary")), "summary 必须有证据映射")
    add_check("evidence.core_beliefs", nonempty_list(evidence_map.get("core_beliefs")), "core_beliefs 必须有证据映射")
    add_check("evidence.boundaries", nonempty_list(evidence_map.get("boundaries")), "boundaries 必须有证据映射")
    add_check("evidence.thinking_style", nonempty_list(evidence_map.get("thinking_style")), "thinking_style 必须有证据映射")

    final_ready = all(item["ok"] for item in checks)
    recommended_status = "final" if final_ready else "draft"
    current_status = str(meta.get("draft_status", "draft")).strip() or "draft"
    return {
        "final_ready": final_ready,
        "recommended_draft_status": recommended_status,
        "current_draft_status": current_status,
        "status_matches_recommendation": current_status == recommended_status,
        "failed_checks": [item for item in checks if not item["ok"]],
        "checks": checks,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "# clone_config_validation",
        "",
        f"final_ready: {str(report['final_ready']).lower()}",
        f"recommended_draft_status: {report['recommended_draft_status']}",
        f"current_draft_status: {report['current_draft_status']}",
        f"status_matches_recommendation: {str(report['status_matches_recommendation']).lower()}",
        "",
        "failed_checks:",
    ]
    for item in report["failed_checks"]:
        lines.append(f"- {item['name']}: {item['detail']}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate clone_config.yaml release readiness.")
    parser.add_argument("--input", required=True, help="Path to clone_config.yaml")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_simple_yaml(Path(args.input))
    report = validate(config)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report), end="")
    return 0 if report["status_matches_recommendation"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
