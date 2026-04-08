#!/usr/bin/env python3
"""Build a runnable workflow-clone skill directory from clone config and workflow blueprint."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from manifest_utils import build_source_artifacts
except ModuleNotFoundError:
    from scripts.manifest_utils import build_source_artifacts


def slugify(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "workflow-clone"


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


def split_h2_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^##\s+(.+?)\n(.*?)(?=^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def bullet_list(items: list[str], default: str) -> str:
    clean = [item.strip() for item in items if item.strip()]
    if not clean:
        return f"- {default}"
    return "\n".join(f"- {item}" for item in clean)


def extract_bullets(text: str) -> list[str]:
    values = []
    for line in normalize_lines(text):
        if line.startswith("- "):
            values.append(line[2:].strip())
    return values


def clean_stage_title(title: str) -> str:
    return re.sub(r"^\d+\.\s*", "", title).strip()


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_template(path: Path, values: dict[str, str]) -> str:
    return path.read_text(encoding="utf-8").format(**values)


def parse_workflow_blueprint(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else "未命名工作流"
    h2 = split_h2_sections(text)
    positioning = extract_bullets(h2.get("定位", ""))
    interview = split_h3_sections(h2.get("通用访谈答案", ""))
    stages = split_h3_sections(h2.get("阶段蓝图", ""))
    actions = split_h3_sections(h2.get("阶段动作", ""))
    tools = split_h3_sections(h2.get("工具映射", ""))
    transitions = split_h3_sections(h2.get("阶段切换规则", ""))
    checkpoints = split_h3_sections(h2.get("人工介入点", ""))
    state = extract_bullets(h2.get("状态记录", ""))
    delivery = extract_bullets(h2.get("交付约定", ""))
    return {
        "title": title,
        "positioning": positioning,
        "interview": interview,
        "stages": stages,
        "actions": actions,
        "tools": tools,
        "transitions": transitions,
        "checkpoints": checkpoints,
        "state": state,
        "delivery": delivery,
    }


def infer_skill_name(config: dict[str, Any], workflow_title: str) -> str:
    profession = str(config.get("meta", {}).get("profession", "")).strip()
    suffix = slugify(profession or workflow_title)
    return f"workflow-clone-{suffix}"


def render_stage_execution(stages: dict[str, str]) -> str:
    if not stages:
        return "暂无阶段定义"
    parts: list[str] = []
    for idx, (name, body) in enumerate(stages.items(), start=1):
        parts.append(f"### {idx}. {clean_stage_title(name)}")
        parts.append("")
        parts.extend(normalize_lines(body))
        parts.append("")
    return "\n".join(parts).strip()


def render_named_sections(data: dict[str, str], default_title: str) -> str:
    if not data:
        return f"- 暂无{default_title}"
    parts: list[str] = []
    for name, body in data.items():
        parts.append(f"### {name}")
        parts.append("")
        parts.extend(normalize_lines(body))
        parts.append("")
    return "\n".join(parts).strip()


def render_stage_decision_protocol(stages: dict[str, str]) -> str:
    ordered = [clean_stage_title(name) for name in stages.keys()]
    if not ordered:
        ordered = ["未定义阶段"]
    text = "\n".join(f"- {name}" for name in ordered)
    return (
        "每次收到任务后，先判断当前任务属于哪一阶段。\n"
        "判断顺序：\n"
        f"{text}\n"
        "- 如果输入还不能支撑进入下一阶段，停留在当前阶段并明确缺口。\n"
        "- 如果命中人工介入点，不继续自动推进，改为输出升级请求。\n"
        "- 如果当前阶段已满足完成判断，才进入下一阶段。"
    )


def render_response_contract() -> str:
    return """每次执行时，输出必须至少包含这 6 项：

- `current_stage`: 当前判断所处阶段
- `objective`: 当前阶段的目标
- `done`: 本轮已完成什么
- `next_action`: 下一步明确动作
- `needs_user`: 是否需要人工介入；若需要，写清原因
- `deliverable`: 当前已形成的产物或尚缺的产物

如果需要人工介入，额外补：

- `risk`: 风险是什么
- `decision_needed`: 需要本人决定什么
- `why_blocked`: 为什么现在不能自动继续"""


def render_skill_md(config: dict[str, Any], workflow: dict[str, Any]) -> str:
    meta = config.get("meta", {})
    identity = config.get("identity", {})
    expression = config.get("expression", {})
    draft_status = str(meta.get("draft_status", "draft")).strip() or "draft"
    created_at = str(meta.get("created_at", "unknown")).strip() or "unknown"
    clone_name = str(meta.get("name", "")).strip() or "工作型分身"
    profession = str(meta.get("profession", "")).strip()
    quality_score = meta.get("quality_score", 0)
    expertise = identity.get("expertise", [])
    boundaries = identity.get("boundaries", [])
    if not isinstance(expertise, list):
        expertise = []
    if not isinstance(boundaries, list):
        boundaries = []

    workflow_name = workflow["title"]
    skill_name = infer_skill_name(config, workflow_name)
    description = (
        f"{clone_name} 的工作型分身。当用户希望按“{workflow_name}”这类固定流程推进任务、"
        "分阶段执行、并在关键节点请求人工拍板时激活。"
    )

    return f"""---
name: {skill_name}
description: >
  {description}
metadata:
  openclaw:
    emoji: "⚙️"
    clone:
      type: "workflow"
      version: "1.0"
      created_at: {yaml_quote(created_at)}
      profession: {yaml_quote(profession)}
      workflow_name: {yaml_quote(workflow_name)}
      based_on: {yaml_quote(clone_name)}
      draft_status: {yaml_quote(draft_status)}
      quality_score: {quality_score if isinstance(quality_score, int) else 0}
    requires:
      config:
        - "clone.identity_confirmed"
        - "workflow.blueprint_present"
---

# {clone_name} 工作型分身

> 生成时间 / Generated At: {created_at}
> 版本 / Version: v1.0
> 草稿状态 / Draft Status: {draft_status}
> 质量评分 / Quality Score: {quality_score if isinstance(quality_score, int) else 0}/100

## 身份声明

你不是只负责“像本人回答”，而是要按既定工作流推进 `{workflow_name}` 这类任务。
你继承 `{clone_name}` 的判断风格、边界和表达方式，但你的首要职责是推进任务，而不是只给建议。

## 适用范围

适合这类工作：
{bullet_list(workflow.get("positioning", []), "暂无")}

该分身的能力基础：
{bullet_list([*expertise[:6]], "暂无明确能力基础")}

明确边界：
{bullet_list([*boundaries[:6]], "暂无明确边界")}

## 激活规则

- 当用户明确希望你替他推进 `{workflow_name}` 这类工作时激活
- 当任务可以被拆进既定阶段并存在明确交付物时激活
- 当遇到高风险决策、需求冲突、权限缺失时，暂停自动推进并请求人工确认

## 任务接收协议

- 先把用户输入收束成一个具体任务，不要同时推进多个工作单元
- 如果任务目标不清，优先进入最前面的澄清阶段，而不是直接执行
- 如果任务不属于 `{workflow_name}` 的适用范围，明确拒绝套用该流程
- 每轮推进都要明确当前阶段、阶段目标、已知输入和当前缺口

## 工作流入口

### 触发条件

{workflow.get("interview", {}).get("W1. 触发条件", workflow.get("interview", {}).get("W1. 这类工作从什么触发？", "暂无"))}

### 完成标准

{workflow.get("interview", {}).get("W2. 完成标准", workflow.get("interview", {}).get("W2. 完成的标准是什么？", "暂无"))}

### 常见阻塞

{bullet_list(extract_bullets(workflow.get("interview", {}).get("W5. 常见阻塞", workflow.get("interview", {}).get("W5. 哪些环节最容易卡住？", ""))), "暂无")}

## 阶段执行规则

{render_stage_execution(workflow.get("stages", {}))}

## 阶段动作

{render_named_sections(workflow.get("actions", {}), "阶段动作")}

## 工具调用规则

{render_named_sections(workflow.get("tools", {}), "工具映射")}

## 阶段切换规则

{render_named_sections(workflow.get("transitions", {}), "阶段切换规则")}

## 人工介入点

{render_named_sections(workflow.get("checkpoints", {}), "人工介入点")}

## 阶段判断协议

{render_stage_decision_protocol(workflow.get("stages", {}))}

## 状态记录要求

{bullet_list(workflow.get("state", []), "当前阶段")}

## 执行输出协议

{render_response_contract()}

## 交付要求

{bullet_list(workflow.get("delivery", []), "最终结果")}

## 表达方式

- 语言风格：{str(expression.get("language_style", "")).strip() or "直接、清楚、务实。"}
- 回答结构：{str(expression.get("response_format", "")).strip() or "先结论，再说明下一步。"}
- 当你暂停请求人工介入时，必须明确说清：卡在哪一阶段、缺什么、为什么不能继续。

## 执行优先级

1. 先判断当前任务是否属于 `{workflow_name}` 的适用范围。
2. 先定位当前阶段，再决定下一步动作，不要跳步给泛泛建议。
3. 默认推进到下一个明确产出，除非触发人工介入点。
4. 不要把高风险决策伪装成自动结论。

## 当前状态

- draft_status: `{draft_status}`
- quality_score: `{quality_score}/100`
- based_on_clone: `{clone_name}`
- workflow_name: `{workflow_name}`
"""


def copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def validate_adapters(skill_root: Path) -> dict[str, Any]:
    validator = skill_root / "scripts" / "validate_profession_adapters.py"
    if not validator.exists():
        return {"valid": True, "adapter_count": 0, "results": [], "skipped": True}
    with tempfile.TemporaryDirectory(prefix="profession-adapter-validation-") as tmpdir:
        output = Path(tmpdir) / "validation.json"
        proc = subprocess.run(
            ["python3", str(validator), "--workspace", str(skill_root), "--output", str(output)],
            cwd=skill_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if not output.exists():
            raise SystemExit(f"profession adapter validation did not produce output: {proc.stderr.strip()}")
        data = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SystemExit("profession adapter validation returned invalid JSON")
        if proc.returncode != 0 or not data.get("valid", False):
            errors: list[str] = []
            for item in data.get("results", []):
                if not isinstance(item, dict) or item.get("valid", False):
                    continue
                file_path = str(item.get("file", "")).strip() or "<unknown>"
                for error in item.get("errors", []):
                    errors.append(f"{file_path}: {error}")
            detail = "\n".join(errors) if errors else (proc.stderr.strip() or "unknown validation error")
            raise SystemExit(f"profession adapter validation failed:\n{detail}")
        return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a workflow clone skill directory from clone config and workflow blueprint."
    )
    parser.add_argument("--clone-config", required=True)
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--mind-profile")
    parser.add_argument("--system-prompt")
    parser.add_argument("--task-state")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--skill-base",
        default="assets/workflow-clone-skill-base",
        help="Base directory for workflow clone skill",
    )
    parser.add_argument("--skip-adapter-validation", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    clone_config = Path(args.clone_config)
    workflow_blueprint = Path(args.workflow_blueprint)
    output_dir = Path(args.output_dir)
    skill_base = Path(args.skill_base)
    skill_root = Path(__file__).resolve().parent.parent

    if not clone_config.exists():
        raise SystemExit(f"clone config not found: {clone_config}")
    if not workflow_blueprint.exists():
        raise SystemExit(f"workflow blueprint not found: {workflow_blueprint}")
    if not skill_base.exists():
        raise SystemExit(f"workflow skill base not found: {skill_base}")
    if not args.skip_adapter_validation:
        validate_adapters(skill_root)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(skill_base, output_dir)

    config = load_simple_yaml(clone_config)
    workflow = parse_workflow_blueprint(workflow_blueprint)

    (output_dir / "SKILL.md").write_text(
        render_skill_md(config, workflow),
        encoding="utf-8",
    )
    copy_if_exists(clone_config, output_dir / "clone_config.yaml")
    copy_if_exists(workflow_blueprint, output_dir / "workflow_blueprint.md")
    if args.mind_profile:
        copy_if_exists(Path(args.mind_profile), output_dir / "mind_profile.md")
    if args.system_prompt:
        copy_if_exists(Path(args.system_prompt), output_dir / "system_prompt.md")
    if args.task_state:
        copy_if_exists(Path(args.task_state), output_dir / "workflow_task_state.yaml")
    copied_mind_profile = output_dir / "mind_profile.md"
    copied_system_prompt = output_dir / "system_prompt.md"
    copied_task_state = output_dir / "workflow_task_state.yaml"
    positioning = workflow.get("positioning", [])
    if not isinstance(positioning, list):
        positioning = []
    stage_names = [clean_stage_title(name) for name in workflow.get("stages", {}).keys()] if isinstance(workflow.get("stages", {}), dict) else []
    manifest = {
        "type": "workflow_clone_skill",
        "clone_name": str(config.get("meta", {}).get("name", "")).strip() or "工作型分身",
        "profession": str(config.get("meta", {}).get("profession", "")).strip(),
        "workflow_name": workflow.get("title", "未命名工作流"),
        "draft_status": str(config.get("meta", {}).get("draft_status", "draft")).strip() or "draft",
        "quality_score": config.get("meta", {}).get("quality_score", 0),
        "source_artifacts": build_source_artifacts(
            {
                "clone_config": Path(args.clone_config).resolve(),
                "workflow_blueprint": Path(args.workflow_blueprint).resolve(),
                "mind_profile": Path(args.mind_profile).resolve() if args.mind_profile else None,
                "system_prompt": Path(args.system_prompt).resolve() if args.system_prompt else None,
                "workflow_task_state": Path(args.task_state).resolve() if args.task_state else None,
            }
        ),
        "files": {
            "skill_md": str(output_dir / "SKILL.md"),
            "clone_config": str(output_dir / "clone_config.yaml"),
            "workflow_blueprint": str(output_dir / "workflow_blueprint.md"),
            "mind_profile": str(copied_mind_profile) if copied_mind_profile.exists() else "",
            "system_prompt": str(copied_system_prompt) if copied_system_prompt.exists() else "",
            "workflow_task_state": str(copied_task_state) if copied_task_state.exists() else "",
        },
    }
    manifest_path = output_dir / "workflow_clone_skill_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    readme_template = skill_root / "templates" / "workflow_clone_skill_readme_template.md"
    if readme_template.exists():
        (output_dir / "README.md").write_text(
            render_template(
                readme_template,
                {
                    "clone_name": manifest["clone_name"],
                    "profession": manifest["profession"] or "未指定",
                    "workflow_name": manifest["workflow_name"],
                    "draft_status": manifest["draft_status"],
                    "quality_score": str(manifest["quality_score"]),
                    "skill_md": manifest["files"]["skill_md"],
                    "clone_config": manifest["files"]["clone_config"],
                    "workflow_blueprint": manifest["files"]["workflow_blueprint"],
                    "mind_profile": manifest["files"]["mind_profile"],
                    "system_prompt": manifest["files"]["system_prompt"],
                    "workflow_task_state": manifest["files"]["workflow_task_state"],
                    "manifest": str(manifest_path),
                    "positioning_summary": "；".join(str(x) for x in positioning[:4]) or "暂无明确定位摘要",
                    "stage_summary": " -> ".join(stage_names[:6]) or "暂无明确阶段摘要",
                },
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
