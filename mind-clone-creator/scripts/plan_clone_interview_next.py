#!/usr/bin/env python3
"""Plan the next interview question for persona/workflow clone creation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PERSONAL_ITEMS = [
    ("A1. 用 3 句话介绍自己", "A 区", "请先用 3 句话介绍自己：你做什么、最擅长什么、别人为什么会来找你。", "prompts/interview_guide.md"),
    ("A2. 能力地图", "A 区", "补你的能力地图：顶级能力、熟练能力、边界各写 1-3 条，尽量贴近真实工作。", "prompts/interview_guide.md"),
    ("A3. 知识来源", "A 区", "补你的知识来源：哪些书、作者、领域、学习方式最影响你的判断。", "prompts/interview_guide.md"),
    ("A4. 如何定义自己的工作价值", "A 区", "补你如何定义自己的工作价值：你解决什么问题，别人为什么找你。", "prompts/interview_guide.md"),
    ("B1. 你如何分析一个新问题", "B 区", "用一个最近的真实问题，写出你怎么分析、推进并得出结论。", "prompts/interview_guide.md"),
    ("B2. 最常用的思维框架", "B 区", "列出你真正常用的思维框架，并写清在哪类场景会用。", "prompts/interview_guide.md"),
    ("B3. 如何处理信息不足", "B 区", "写你在信息不足时怎么做，并补一个真实例子。", "prompts/interview_guide.md"),
    ("B4. 最容易忽略的视角", "B 区", "写你的盲区：你自己知道的，以及别人提醒过你的。", "prompts/interview_guide.md"),
    ("C1. 核心信念", "C 区", "至少写 3 条核心信念，每条都补一个最小例子或真实动作。", "prompts/interview_guide.md"),
    ("C2. 优先级排序", "C 区", "写清你在速度/质量、短期/长期、确定性/可能性之间怎么真实取舍。", "prompts/interview_guide.md"),
    ("C3. 红线", "C 区", "写你会直接拒绝的事，以及为什么。", "prompts/interview_guide.md"),
    ("C4. 如何定义“好的建议”", "C 区", "写你认为什么是好建议、最反感什么建议方式、希望分身给人什么感觉。", "prompts/interview_guide.md"),
    ("D1. 口语化自我描述", "D 区", "用你平时说话的方式，描述一件最近做的事，避免书面腔。", "prompts/interview_guide.md"),
    ("D2. 表达偏好", "D 区", "补你的表达偏好：先结论还是先铺垫、偏好框架还是数据、回答长短。", "prompts/interview_guide.md"),
    ("D3. 不喜欢的表达方式", "D 区", "写你最讨厌和最欣赏的回答风格。", "prompts/interview_guide.md"),
    ("E1. 3 个最常被问到的问题 + 真实回答", "E 区", "补 3 个别人最常问你的问题，并写出你真实会怎么答。", "prompts/interview_guide.md"),
    ("E2. 一个你有明确立场但可能有人不同意的问题", "E 区", "写一个你有明确立场的问题，并说明理由和局限。", "prompts/interview_guide.md"),
    ("E3. 完全不擅长的问题，你怎么回应（示范）", "E 区", "示范一个你完全不擅长的问题时你会怎么回应。", "prompts/interview_guide.md"),
    ("E4. 一个解决过的复杂问题", "E 区", "写一个复杂问题的完整处理过程：背景、分析、方案、结果、复盘。", "prompts/interview_guide.md"),
]

WORKFLOW_ITEMS = [
    ("W1. 这类工作从什么触发？", "工作流访谈", "先回答这类工作通常从什么触发，你在什么情况下会正式开始接它。", "prompts/workflow_interview_guide.md"),
    ("W2. 完成的标准是什么？", "工作流访谈", "补完成标准：你怎么判断这件事真的做完了。", "prompts/workflow_interview_guide.md"),
    ("W3. 中间大概经过几个阶段？", "工作流访谈", "补关键阶段，不用很细，但要贴近你的真实顺序。", "prompts/workflow_interview_guide.md"),
    ("W4. 每个阶段你主要用什么工具？", "工作流访谈", "补每个阶段会用的软件、平台、方法或协作对象。", "prompts/workflow_interview_guide.md"),
    ("W5. 哪些环节最容易卡住？", "工作流访谈", "补最容易卡住、返工、等待确认的环节。", "prompts/workflow_interview_guide.md"),
    ("W6. 哪些决策必须你本人来做？", "工作流访谈", "补必须由你本人拍板的判断，不要泛写。", "prompts/workflow_interview_guide.md"),
    ("W7. 最终交给对方的是什么？", "工作流访谈", "补最终交付物：文件、方案、代码、文书、记录都可以。", "prompts/workflow_interview_guide.md"),
]

SECTION_RULES: dict[str, dict[str, Any]] = {
    "A1. 用 3 句话介绍自己": {"min_chars": 30, "need_lines": 3},
    "A2. 能力地图": {"min_filled_labels": 3},
    "A3. 知识来源": {"min_filled_labels": 3},
    "A4. 如何定义自己的工作价值": {"min_filled_labels": 2},
    "B1. 你如何分析一个新问题": {"min_filled_labels": 4, "min_chars": 40},
    "B2. 最常用的思维框架": {"min_items": 1},
    "B3. 如何处理信息不足": {"min_chars": 20, "need_example": True},
    "B4. 最容易忽略的视角": {"min_filled_labels": 2},
    "C1. 核心信念": {"min_numbered": 3, "need_example": True},
    "C2. 优先级排序": {"min_filled_labels": 3},
    "C3. 红线": {"min_items": 1, "need_reason": True},
    "C4. 如何定义“好的建议”": {"min_filled_labels": 3},
    "D1. 口语化自我描述": {"min_chars": 40},
    "D2. 表达偏好": {"min_filled_labels": 3},
    "D3. 不喜欢的表达方式": {"min_filled_labels": 2},
    "E1. 3 个最常被问到的问题 + 真实回答": {"min_qa_pairs": 3},
    "E2. 一个你有明确立场但可能有人不同意的问题": {"min_filled_labels": 3, "need_reason": True},
    "E3. 完全不擅长的问题，你怎么回应（示范）": {"min_chars": 12},
    "E4. 一个解决过的复杂问题": {"min_filled_labels": 5, "need_example": True},
    "W1. 这类工作从什么触发？": {"min_chars": 12},
    "W2. 完成的标准是什么？": {"min_chars": 12},
    "W3. 中间大概经过几个阶段？": {"min_numbered": 3},
    "W4. 每个阶段你主要用什么工具？": {"min_chars": 12},
    "W5. 哪些环节最容易卡住？": {"min_chars": 12},
    "W6. 哪些决策必须你本人来做？": {"min_chars": 12},
    "W7. 最终交给对方的是什么？": {"min_chars": 8},
}

REASON_FOLLOW_UPS: dict[str, dict[str, str]] = {
    "内容过短": {
        "question": "这题先别只写结论，再补一点具体内容，至少把场景和做法说出来。",
        "example_hint": "补一个最近项目、真实场景或一句你当时的动作。",
    },
    "要点数量不足": {
        "question": "这一题按原要求补满关键点，不要只写其中一部分。",
        "example_hint": "如果是三句话介绍自己，就分别补“做什么、擅长什么、别人为什么找你”。",
    },
    "关键字段未填满": {
        "question": "这一题还有关键字段没填满，按每个标签各补一句。",
        "example_hint": "优先补还空着的冒号字段，每个字段至少给一个真实说法。",
    },
    "编号项不足": {
        "question": "编号项数量还不够，请至少按要求补全每一项。",
        "example_hint": "每一项尽量对应一个独立原则、阶段或问题，不要合并在一起。",
    },
    "条目数量不足": {
        "question": "这一题的条目还不够，请再补至少一条。",
        "example_hint": "优先补最常见、最有代表性的那一条。",
    },
    "问答对数量不足": {
        "question": "常见问答还没补满，请再补完整的问答对。",
        "example_hint": "每组都写清“别人怎么问”和“你会怎么答”。",
    },
    "缺少具体例子": {
        "question": "这题现在有观点，但还缺一个真实例子来锚定，不然太像通用描述。",
        "example_hint": "可以给项目名、场景词、指标词，或者一句你当时先做的动作。",
    },
    "缺少原因或局限说明": {
        "question": "这题还需要补“为什么”或“局限在哪”，不然判断依据不完整。",
        "example_hint": "补一句因为/所以，或者补一句你承认的边界和代价。",
    },
    "尚未填写": {
        "question": "这一题还没开始写，先补最基本的回答。",
        "example_hint": "先给最常见情况，不必追求一次写满。",
    },
}


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines()]


def has_substantive_content(text: str) -> bool:
    placeholders = {"", "-", "1.", "2.", "3.", "回答：", "例子：", "问：", "答："}
    for line in normalize_lines(text):
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        if line in placeholders:
            continue
        if re.match(r"^\d+\.\s*$", line):
            continue
        if line.startswith("- ") and not line[2:].strip():
            continue
        if line.startswith(("1. 问：", "2. 问：", "3. 问：")):
            continue
        if "：" in line:
            _, value = line.split("：", 1)
            if value.strip():
                return True
            continue
        if line.startswith("- "):
            if line[2:].strip():
                return True
            continue
        if re.match(r"^\d+\.\s+\S+", line):
            return True
        return True
    return False


def count_filled_labels(text: str) -> int:
    count = 0
    for line in normalize_lines(text):
        if "：" not in line:
            continue
        _, value = line.split("：", 1)
        if value.strip():
            count += 1
    return count


def count_numbered_items(text: str) -> int:
    count = 0
    for line in normalize_lines(text):
        if re.match(r"^\d+\.\s+\S+", line):
            count += 1
    return count


def count_bullet_items(text: str) -> int:
    count = 0
    for line in normalize_lines(text):
        if line.startswith("- ") and line[2:].strip():
            count += 1
    return count


def count_qa_pairs(text: str) -> int:
    pairs = 0
    current_has_q = False
    for line in normalize_lines(text):
        if "问：" in line:
            current_has_q = True
        elif current_has_q and "答：" in line:
            _, value = line.split("答：", 1)
            if value.strip():
                pairs += 1
                current_has_q = False
    return pairs


def non_placeholder_char_count(text: str) -> int:
    chars = 0
    for line in normalize_lines(text):
        cleaned = line
        for prefix in ("- ", "问：", "答：", "例子："):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
        if "：" in cleaned and cleaned.split("：", 1)[1].strip():
            cleaned = cleaned.split("：", 1)[1].strip()
        chars += len(cleaned.strip())
    return chars


def assess_section_content(title: str, text: str) -> dict[str, Any]:
    rules = SECTION_RULES.get(title, {})
    if not has_substantive_content(text):
        reasons = ["尚未填写"]
        return {
            "status": "missing",
            "reasons": reasons,
            "follow_up_prompt": "先补这一题的基本回答。",
            "follow_up_strategy": build_follow_up_strategy(title, reasons, rules),
        }
    reasons: list[str] = []
    if rules.get("min_chars") and non_placeholder_char_count(text) < int(rules["min_chars"]):
        reasons.append("内容过短")
    if rules.get("need_lines"):
        filled_lines = [line for line in normalize_lines(text) if line.startswith("- ") and line[2:].strip()]
        if len(filled_lines) < int(rules["need_lines"]):
            reasons.append("要点数量不足")
    if rules.get("min_filled_labels") and count_filled_labels(text) < int(rules["min_filled_labels"]):
        reasons.append("关键字段未填满")
    if rules.get("min_numbered") and count_numbered_items(text) < int(rules["min_numbered"]):
        reasons.append("编号项不足")
    if rules.get("min_items") and count_bullet_items(text) < int(rules["min_items"]):
        reasons.append("条目数量不足")
    if rules.get("min_qa_pairs") and count_qa_pairs(text) < int(rules["min_qa_pairs"]):
        reasons.append("问答对数量不足")
    lowered = text.lower()
    if rules.get("need_example") and not any(token in text for token in ["例如", "比如", "例子", "项目", "场景"]) and "上次" not in text:
        reasons.append("缺少具体例子")
    if rules.get("need_reason") and not any(token in text for token in ["因为", "所以", "原因", "局限"]):
        reasons.append("缺少原因或局限说明")
    status = "sufficient" if not reasons else "insufficient"
    follow_up = "当前内容已基本充分，可以继续下一题。"
    if reasons:
        follow_up = f"建议补充：{'、'.join(reasons)}。"
    follow_up_strategy = build_follow_up_strategy(title, reasons, rules)
    return {
        "status": status,
        "reasons": reasons,
        "follow_up_prompt": follow_up,
        "follow_up_strategy": follow_up_strategy,
    }


def build_follow_up_strategy(title: str, reasons: list[str], rules: dict[str, Any]) -> dict[str, Any]:
    if not reasons:
        return {
            "question": "",
            "example_hint": "",
            "example_required": bool(rules.get("need_example", False)),
            "must_answer_before_continue": False,
        }
    primary = reasons[0]
    preset = REASON_FOLLOW_UPS.get(primary, REASON_FOLLOW_UPS["尚未填写"])
    must_answer = primary == "尚未填写"
    if primary in {"关键字段未填满", "编号项不足", "问答对数量不足"}:
        must_answer = True
    return {
        "question": preset["question"],
        "example_hint": preset["example_hint"],
        "example_required": bool(rules.get("need_example", False)),
        "must_answer_before_continue": must_answer,
    }


def extract_workflow_answer_body(text: str) -> str:
    if "回答：" not in text:
        return text
    return text.split("回答：", 1)[1].strip()


def evaluate_sections(
    path: Path,
    items: list[tuple[str, str, str, str]],
    kind: str = "personal",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    sections = split_h3_sections(text)
    answered = 0
    sufficient = 0
    next_item: dict[str, str] | None = None
    section_statuses: list[dict[str, Any]] = []
    overrides = overrides or {}
    for title, phase, prompt, guide in items:
        body = sections.get(title, "")
        inspect_body = extract_workflow_answer_body(body) if kind == "workflow" else body
        assessment = assess_section_content(title, inspect_body)
        override = overrides.get(title, {})
        override_status = str(override.get("status", "")).strip()
        if override_status in {"confirmed", "accepted_for_now", "accepted_final"}:
            final_ready = override_status == "accepted_final"
            assessment = {
                "status": "sufficient",
                "reasons": ["人工确认先通过" if not final_ready else "人工确认最终通过"],
                "follow_up_prompt": "该题已被人工确认可先通过。" if not final_ready else "该题已被人工确认最终通过。",
                "follow_up_strategy": {
                    "question": "",
                    "example_hint": "",
                    "example_required": False,
                    "must_answer_before_continue": False,
                },
                "override_applied": True,
                "override_status": override_status,
                "final_ready": final_ready,
            }
        else:
            assessment["override_applied"] = False
            assessment["override_status"] = ""
            assessment["final_ready"] = assessment["status"] == "sufficient"
        section_status = {
            "section": title,
            "phase": phase,
            "status": assessment["status"],
            "reasons": assessment["reasons"],
            "follow_up_prompt": assessment["follow_up_prompt"],
            "follow_up_strategy": assessment["follow_up_strategy"],
            "override_applied": assessment["override_applied"],
            "override_status": assessment["override_status"],
            "final_ready": assessment["final_ready"],
        }
        section_statuses.append(section_status)
        if assessment["status"] != "missing":
            answered += 1
        if assessment["status"] == "sufficient":
            sufficient += 1
        if next_item is None and assessment["status"] != "sufficient":
            next_item = {
                "section": title,
                "phase": phase,
                "prompt": prompt,
                "guide": guide,
                "assessment": assessment["status"],
                "reasons": assessment["reasons"],
                "follow_up_prompt": assessment["follow_up_prompt"],
                "follow_up_strategy": assessment["follow_up_strategy"],
                "override_applied": assessment["override_applied"],
                "override_status": assessment["override_status"],
                "final_ready": assessment["final_ready"],
            }
    return {
        "exists": path.exists(),
        "answered": answered,
        "sufficient": sufficient,
        "final_ready_count": sum(1 for item in section_statuses if item["final_ready"]),
        "total": len(items),
        "ready": sufficient >= len(items),
        "final_ready": all(item["final_ready"] for item in section_statuses),
        "next_item": next_item,
        "section_statuses": section_statuses,
    }


def render_markdown(status: dict[str, Any]) -> str:
    next_item = status.get("next_item") or {}
    lines = [
        "# Clone Interview Status",
        "",
        "## Progress",
        "",
        f"- personal_interview_ready: {str(status['personal']['ready']).lower()}",
        f"- workflow_interview_ready: {str(status['workflow']['ready']).lower() if status['workflow'] else 'n/a'}",
        f"- overall_status: {status['overall_status']}",
        "",
        "## Completion",
        "",
        f"- personal_answered: {status['personal']['answered']} / {status['personal']['total']}",
        f"- personal_sufficient: {status['personal']['sufficient']} / {status['personal']['total']}",
        f"- personal_final_ready: {status['personal']['final_ready_count']} / {status['personal']['total']}",
    ]
    if status["workflow"]:
        lines.append(f"- workflow_answered: {status['workflow']['answered']} / {status['workflow']['total']}")
        lines.append(f"- workflow_sufficient: {status['workflow']['sufficient']} / {status['workflow']['total']}")
        lines.append(f"- workflow_final_ready: {status['workflow']['final_ready_count']} / {status['workflow']['total']}")
    lines.extend(
        [
            "",
            "## Next Question",
            "",
            f"- target_file: {status['next_target_file']}",
            f"- phase: {next_item.get('phase', '无')}",
            f"- section: {next_item.get('section', '无')}",
            f"- assessment: {next_item.get('assessment', 'n/a')}",
            f"- reasons: {', '.join(next_item.get('reasons', [])) or '无'}",
            f"- prompt: {next_item.get('prompt', '当前访谈已完整，可继续构建。')}",
            f"- follow_up_prompt: {next_item.get('follow_up_prompt', '无')}",
            f"- follow_up_question: {(next_item.get('follow_up_strategy') or {}).get('question', '无')}",
            f"- example_hint: {(next_item.get('follow_up_strategy') or {}).get('example_hint', '无')}",
            f"- example_required: {str((next_item.get('follow_up_strategy') or {}).get('example_required', False)).lower()}",
            f"- must_answer_before_continue: {str((next_item.get('follow_up_strategy') or {}).get('must_answer_before_continue', False)).lower()}",
            f"- override_status: {next_item.get('override_status', '') or '无'}",
            f"- final_ready: {str(next_item.get('final_ready', False)).lower()}",
            f"- prompt_reference: {next_item.get('guide', '无')}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan the next interview question for clone creation.")
    parser.add_argument("--personal-interview", required=True)
    parser.add_argument("--workflow-interview")
    parser.add_argument("--state")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md")
    return parser.parse_args()


def load_state_overrides(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    overrides = data.get("section_overrides", {})
    return overrides if isinstance(overrides, dict) else {}


def main() -> int:
    args = parse_args()
    personal_path = Path(args.personal_interview).resolve()
    workflow_path = Path(args.workflow_interview).resolve() if args.workflow_interview else None
    state_path = Path(args.state).resolve() if args.state else None
    overrides = load_state_overrides(state_path)
    personal_overrides = overrides.get("personal", {}) if isinstance(overrides.get("personal", {}), dict) else {}
    workflow_overrides = overrides.get("workflow", {}) if isinstance(overrides.get("workflow", {}), dict) else {}

    personal = evaluate_sections(personal_path, PERSONAL_ITEMS, kind="personal", overrides=personal_overrides)
    workflow = (
        evaluate_sections(workflow_path, WORKFLOW_ITEMS, kind="workflow", overrides=workflow_overrides)
        if workflow_path
        else None
    )

    overall_status = "ready_for_build"
    next_item = None
    next_target_file = ""
    if not personal["ready"]:
        overall_status = "needs_personal_interview"
        next_item = personal["next_item"]
        next_target_file = str(personal_path)
    elif workflow and not workflow["ready"]:
        overall_status = "needs_workflow_interview"
        next_item = workflow["next_item"]
        next_target_file = str(workflow_path)

    status = {
        "overall_status": overall_status,
        "personal": personal,
        "workflow": workflow,
        "next_item": next_item or {},
        "next_target_file": next_target_file,
    }

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(render_markdown(status), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
