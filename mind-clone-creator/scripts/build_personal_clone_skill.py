#!/usr/bin/env python3
"""Package clone artifacts into a runnable personal clone skill directory."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

try:
    from manifest_utils import build_source_artifacts
    from render_delivery_summary import (
        build_summary as build_delivery_summary,
        build_workflow_summary,
        detect_working_bundle_manifest,
        render_markdown as render_delivery_markdown,
    )
except ModuleNotFoundError:
    from scripts.manifest_utils import build_source_artifacts
    from scripts.render_delivery_summary import (
        build_summary as build_delivery_summary,
        build_workflow_summary,
        detect_working_bundle_manifest,
        render_markdown as render_delivery_markdown,
    )


def slugify(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "personal-clone"


def parse_scalar(text: str) -> Any:
    if text == "null":
        return None
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
            value = parse_scalar(line[2:].strip())
            if isinstance(parent, list):
                parent.append(value)
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


def infer_skill_slug(config: dict[str, Any], clone_name: str) -> str:
    profession = str(config.get("meta", {}).get("profession", "")).strip().lower()
    profession = re.sub(r"[^a-z0-9]+", "-", profession).strip("-")
    if profession:
        return f"clone-{profession}"
    return f"clone-{slugify(clone_name)}"


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def render_metadata_yaml(
    skill_name: str,
    clone_name: str,
    profession: str,
    quality_score: int,
    draft_status: str,
    created_at: str,
    expertise: list[str],
) -> str:
    lines = [
        f"name: {skill_name}",
        "description: >",
        f"  {clone_name} 的数字分身。当用户想咨询 {profession or '相关领域'} 问题、",
        "  寻求其核心能力方向的建议时激活。",
        f"  分身基于本人结构化自我访谈构建，还原度约 {quality_score}%。",
        "metadata:",
        "  openclaw:",
        '    emoji: "🧠"',
        "    clone:",
        '      type: "personal"',
        '      version: "1.0"',
        f"      quality_score: {quality_score}",
        f"      draft_status: {yaml_quote(draft_status)}",
        f"      created_at: {yaml_quote(created_at)}",
        f"      profession: {yaml_quote(profession)}",
        "      expertise:",
    ]
    if expertise:
        lines.extend([f"        - {yaml_quote(item)}" for item in expertise[:6]])
    else:
        lines.append('        - "未明确"')
    lines.extend(
        [
            "    requires:",
            "      config:",
            '        - "clone.identity_confirmed"',
        ]
    )
    return "\n".join(lines)


def render_bullets(items: list[str], default: str = "暂无") -> str:
    if not items:
        return f"- {default}"
    return "\n".join(f"- {item}" for item in items)


def render_frameworks(items: list[str]) -> str:
    if not items:
        return "- 暂无明确常用框架"
    return "\n".join(f"- {item}" for item in items)


def render_tools(skills: dict[str, Any]) -> str:
    universal = skills.get("universal", {}) if isinstance(skills, dict) else {}
    professional = skills.get("professional", []) if isinstance(skills, dict) else []
    lines: list[str] = []
    if isinstance(universal, dict):
        for name, detail in universal.items():
            if not isinstance(detail, dict):
                continue
            if detail.get("enabled") is False:
                continue
            use_case = detail.get("use_case", "")
            lines.append(f"- {name}: {use_case or '可按配置使用'}")
    if isinstance(professional, list):
        for item in professional[:6]:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "未命名能力")
            trigger = item.get("trigger", "")
            action = item.get("action", "")
            desc = "；".join(part for part in [trigger, action] if part)
            lines.append(f"- {name}: {desc or '按专业能力处理'}")
    return "\n".join(lines) if lines else "- 仅使用当前 personal clone skill 内嵌能力，不额外声明工具。"


def render_runtime_list(items: list[str], default: str) -> str:
    if not items:
        return f"- {default}"
    return "\n".join(f"- {item}" for item in items)


def render_skill_md(config: dict[str, Any], clone_name: str, draft_status: str) -> str:
    meta = config.get("meta", {})
    identity = config.get("identity", {})
    mind_profile = config.get("mind_profile", {})
    expression = config.get("expression", {})
    runtime = config.get("runtime", {})
    skills = config.get("skills", {})
    eval_summary = config.get("eval_summary", {})
    skill_name = infer_skill_slug(config, clone_name)
    profession = meta.get("profession", "")
    quality_score = meta.get("quality_score", 0)
    top_improvement = eval_summary.get("top_improvement", "")
    created_at = str(meta.get("created_at", "")).strip() or "unknown"
    expertise = identity.get("expertise", [])
    boundaries = identity.get("boundaries", [])
    summary = identity.get("summary", "")
    core_beliefs = mind_profile.get("core_beliefs", [])
    thinking_style = str(mind_profile.get("thinking_style", "")).strip()
    frameworks = mind_profile.get("frameworks", [])
    decision_style = str(mind_profile.get("decision_style", "")).strip()
    priority_order = str(mind_profile.get("priority_order", "")).strip()
    work_process = mind_profile.get("work_process", {})
    language_style = str(expression.get("language_style", "")).strip()
    response_format = str(expression.get("response_format", "")).strip()
    avoid = expression.get("avoid", [])

    if not isinstance(expertise, list):
        expertise = []
    if not isinstance(boundaries, list):
        boundaries = []
    if not isinstance(core_beliefs, list):
        core_beliefs = []
    if not isinstance(frameworks, list):
        frameworks = []
    if not isinstance(avoid, list):
        avoid = []
    if not isinstance(work_process, dict):
        work_process = {}
    if not isinstance(runtime, dict):
        runtime = {}

    work_start = str(work_process.get("start", "")).strip()
    work_breakdown = str(work_process.get("breakdown", "")).strip()
    work_delivery = str(work_process.get("delivery_review", "")).strip()
    work_decisions = work_process.get("decision_points", [])
    if not isinstance(work_decisions, list):
        work_decisions = []

    capability_scope = "、".join(expertise[:3]) if expertise else (profession or "该分身覆盖领域")
    boundary_scope = "、".join(boundaries[:2]) if boundaries else "明显超出其能力边界的问题"
    metadata_yaml = render_metadata_yaml(
        skill_name,
        clone_name,
        profession,
        int(quality_score) if isinstance(quality_score, int) else 0,
        draft_status or "draft",
        created_at,
        expertise,
    )
    core_beliefs_text = "\n".join(f"- {item}" for item in core_beliefs) or "- 暂无明确核心信念"
    decision_redlines = render_bullets(boundaries, "暂无明确红线")
    work_process_text = "\n".join(
        [
            line
            for line in [
                f"起手通常是：{work_start}" if work_start else "",
                f"拆解路径通常是：{work_breakdown}" if work_breakdown else "",
                f"关键判断点包括：{'；'.join(work_decisions)}" if work_decisions else "",
                f"交付与复盘方式：{work_delivery}" if work_delivery else "",
            ]
            if line
        ]
    ) or "先定义问题，再拆解，再验证，再交付。"
    top_improvement_line = top_improvement or "暂无"
    boundary_response = (
        "我会明确说明超出范围、指出缺少的关键信息，并在必要时建议转给更合适的人或工具。"
    )
    activation_mode = str(runtime.get("activation_mode", "")).strip() or "always_on"
    exit_commands = runtime.get("exit_commands", [])
    use_this_clone_when = runtime.get("use_this_clone_when", [])
    do_not_use_this_clone_when = runtime.get("do_not_use_this_clone_when", [])
    memory = runtime.get("memory", {})
    if not isinstance(exit_commands, list):
        exit_commands = []
    if not isinstance(use_this_clone_when, list):
        use_this_clone_when = []
    if not isinstance(do_not_use_this_clone_when, list):
        do_not_use_this_clone_when = []
    if not isinstance(memory, dict):
        memory = {}
    remember = memory.get("remember", [])
    forget = memory.get("forget", [])
    if not isinstance(remember, list):
        remember = []
    if not isinstance(forget, list):
        forget = []

    return f"""---
{metadata_yaml}
---

# {clone_name} 数字分身

> 生成时间 / Generated At: {created_at}
> 版本 / Version: v1.0
> 草稿状态 / Draft Status: {draft_status or "draft"}
> 质量评分 / Quality Score: {int(quality_score) if isinstance(quality_score, int) else 0}/100

## 身份声明

你是 {clone_name} 的思维分身。
你基于本人的结构化自我访谈构建，不是那个人本身。
你的目标是用他的思维方式分析问题、给出建议。

还原范围：显性知识、判断框架、表达风格、能力边界。
还原不了：直觉、临场应变、情绪、最新动态。

## 始终激活规则

这个 skill 的激活模式是：`{activation_mode}`。
所有对话都经过这个人格过滤，除非用户明确说出退出命令。
退出命令：
{render_runtime_list(exit_commands, "退出分身模式")}

## 能力范围

**我擅长：**
{render_bullets(expertise, "暂无明确专长")}

**我的边界：**
遇到以下类型的问题，我会明确说明超出我的范围：
{render_bullets(boundaries, "暂无明确边界")}

遇到边界问题时，我的处理方式：
{boundary_response}

## 思维方式

分析问题时，我的习惯流程：
{work_process_text}

我常用的框架：
{render_frameworks(frameworks)}

面对信息不足时：
{thinking_style or "先说明假设与缺口，再决定是否继续判断。"}

## 核心信念

{core_beliefs_text}

## 决策原则

优先级排序：{priority_order or "优先做确定性更高、可验证、可交付的判断。"}
不可逾越的红线：
{decision_redlines}

## 表达方式

语言风格：{language_style or "直接、清楚、少废话。"}
回答结构：{response_format or "先结论，再讲原因。"}
避免：
{render_bullets(avoid, "空泛表达")}

## 不确定性处理

- 基于原始信息的判断：直接陈述
- 推理延伸：标注“这是基于我的思维方式的推测，原文未直接涉及”
- 完全没有覆盖的领域：如实说明，不硬答

## 可用工具

{render_tools(skills)}

## Use This Clone When

{render_runtime_list(use_this_clone_when, f"用户咨询 {profession or '相关领域'} 相关问题")}

## Do Not Use This Clone When

{render_runtime_list(do_not_use_this_clone_when, f"用户需要 {boundary_scope} 的专业帮助")}

## 记忆规则

记住每次对话中：
{render_runtime_list(remember, "用户的核心问题和背景")}

不记住：
{render_runtime_list(forget, "用户的私人信息（除非用户主动要求）")}

## 当前状态

- draft_status: `{draft_status or "draft"}`
- quality_score: `{quality_score}/100`
- most_important_improvement: {top_improvement_line}
"""


def copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_delivery_summary(config: dict[str, Any], clone_config_path: Path, output_path: Path) -> None:
    summary = build_delivery_summary(config, build_workflow_summary(detect_working_bundle_manifest(clone_config_path)))
    output_path.write_text(render_delivery_markdown(summary), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a personal clone skill directory from clone artifacts."
    )
    parser.add_argument("--clone-config", required=True, help="Path to clone_config.yaml")
    parser.add_argument("--mind-profile", help="Path to mind_profile.md")
    parser.add_argument("--system-prompt", help="Path to system_prompt.md")
    parser.add_argument("--eval-report", help="Path to eval_report.md")
    parser.add_argument("--research-digest", help="Path to research_digest.md")
    parser.add_argument("--workflow-blueprint", help="Path to workflow_blueprint.md")
    parser.add_argument("--output-dir", required=True, help="Output skill directory")
    parser.add_argument(
        "--skill-base",
        default="assets/personal-clone-skill-base",
        help="Path to built-in personal clone skill base directory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    clone_config = Path(args.clone_config)
    output_dir = Path(args.output_dir)
    skill_base = Path(args.skill_base)
    skill_root = Path(__file__).resolve().parent.parent

    if not clone_config.exists():
        raise SystemExit(f"clone_config.yaml not found: {clone_config}")
    if not skill_base.exists():
        raise SystemExit(f"skill base not found: {skill_base}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(skill_base, output_dir)

    config = load_simple_yaml(clone_config)
    clone_name = str(config.get("meta", {}).get("name", "")).strip() or output_dir.name
    draft_status = str(config.get("meta", {}).get("draft_status", "draft")).strip() or "draft"

    if draft_status == "final":
        required_artifacts = {
            "mind_profile.md": args.mind_profile,
            "system_prompt.md": args.system_prompt,
            "eval_report.md": args.eval_report,
        }
        missing = [
            name for name, path in required_artifacts.items() if not path or not Path(path).exists()
        ]
        if missing:
            missing_text = ", ".join(missing)
            raise SystemExit(f"final package is missing required artifacts: {missing_text}")

    (output_dir / "SKILL.md").write_text(
        render_skill_md(config, clone_name, draft_status),
        encoding="utf-8",
    )

    copy_if_exists(clone_config, output_dir / "clone_config.yaml")
    if args.mind_profile:
        copy_if_exists(Path(args.mind_profile), output_dir / "mind_profile.md")
    if args.system_prompt:
        copy_if_exists(Path(args.system_prompt), output_dir / "system_prompt.md")
    if args.eval_report:
        copy_if_exists(Path(args.eval_report), output_dir / "eval_report.md")
    if args.research_digest:
        copy_if_exists(Path(args.research_digest), output_dir / "research_digest.md")
    if args.workflow_blueprint:
        copy_if_exists(Path(args.workflow_blueprint), output_dir / "workflow_blueprint.md")
    copied_mind_profile = output_dir / "mind_profile.md"
    copied_system_prompt = output_dir / "system_prompt.md"
    copied_eval_report = output_dir / "eval_report.md"
    copied_research_digest = output_dir / "research_digest.md"
    copied_workflow_blueprint = output_dir / "workflow_blueprint.md"
    delivery_summary_path = output_dir / "DELIVERY_SUMMARY.md"
    write_delivery_summary(config, output_dir / "clone_config.yaml", delivery_summary_path)
    manifest = {
        "type": "personal_clone_skill",
        "clone_name": clone_name,
        "profession": str(config.get("meta", {}).get("profession", "")).strip(),
        "draft_status": draft_status,
        "quality_score": config.get("meta", {}).get("quality_score", 0),
        "source_artifacts": build_source_artifacts(
            {
                "clone_config": clone_config.resolve(),
                "mind_profile": Path(args.mind_profile).resolve() if args.mind_profile else None,
                "system_prompt": Path(args.system_prompt).resolve() if args.system_prompt else None,
                "eval_report": Path(args.eval_report).resolve() if args.eval_report else None,
                "research_digest": Path(args.research_digest).resolve() if args.research_digest else None,
                "workflow_blueprint": Path(args.workflow_blueprint).resolve() if args.workflow_blueprint else None,
            }
        ),
        "files": {
            "skill_md": str(output_dir / "SKILL.md"),
            "clone_config": str(output_dir / "clone_config.yaml"),
            "mind_profile": str(copied_mind_profile) if copied_mind_profile.exists() else "",
            "system_prompt": str(copied_system_prompt) if copied_system_prompt.exists() else "",
            "eval_report": str(copied_eval_report) if copied_eval_report.exists() else "",
            "research_digest": str(copied_research_digest) if copied_research_digest.exists() else "",
            "workflow_blueprint": str(copied_workflow_blueprint) if copied_workflow_blueprint.exists() else "",
            "delivery_summary": str(delivery_summary_path),
        },
    }
    manifest_path = output_dir / "personal_clone_skill_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readme_template = skill_root / "templates" / "personal_clone_skill_readme_template.md"
    if readme_template.exists():
        expertise = config.get("identity", {}).get("expertise", [])
        boundaries = config.get("identity", {}).get("boundaries", [])
        if not isinstance(expertise, list):
            expertise = []
        if not isinstance(boundaries, list):
            boundaries = []
        (output_dir / "README.md").write_text(
            render_template(
                readme_template,
                {
                    "clone_name": clone_name,
                    "profession": str(config.get("meta", {}).get("profession", "")).strip() or "未指定",
                    "draft_status": draft_status,
                    "quality_score": str(config.get("meta", {}).get("quality_score", 0)),
                    "skill_md": manifest["files"]["skill_md"],
                    "clone_config": manifest["files"]["clone_config"],
                    "mind_profile": manifest["files"]["mind_profile"],
                    "system_prompt": manifest["files"]["system_prompt"],
                    "eval_report": manifest["files"]["eval_report"],
                    "research_digest": manifest["files"]["research_digest"],
                    "workflow_blueprint": manifest["files"]["workflow_blueprint"],
                    "manifest": str(manifest_path),
                    "expertise_summary": "；".join(str(x) for x in expertise[:4]) or "暂无明确专长摘要",
                    "boundary_summary": "；".join(str(x) for x in boundaries[:3]) or "暂无明确边界摘要",
                },
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# SCRIPT_REFRESH_MARKER_WORKING

# SCRIPT_REFRESH_MARKER_WORKING

# SCRIPT_REFRESH_MARKER_WORKING

# SCRIPT_REFRESH_MARKER_WORKING

# SCRIPT_REFRESH_MARKER_WORKING

# SCRIPT_REFRESH_MARKER_WORKING

# SCRIPT_REFRESH_MARKER_WORKING
