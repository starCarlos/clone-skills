#!/usr/bin/env python3
"""Extract a structured clone-config draft JSON from markdown artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


UTC_PLUS_8 = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(UTC_PLUS_8).isoformat(timespec="seconds")


def read_text(path: Path | None) -> str:
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def split_h2_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^##\s+(.+?)\n(.*?)(?=^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def normalize_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip().rstrip("  ")
        if line:
            lines.append(line)
    return lines


def extract_bullet_map(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in normalize_lines(text):
        if not line.startswith("- "):
            continue
        body = line[2:].strip()
        if "：" in body:
            key, value = body.split("：", 1)
        elif ":" in body:
            key, value = body.split(":", 1)
        else:
            continue
        result[key.strip()] = value.strip()
    return result


def extract_list_values(text: str) -> list[str]:
    values: list[str] = []
    for line in normalize_lines(text):
        if line.startswith("- "):
            values.append(line[2:].strip())
    return values


def split_cn_list(text: str) -> list[str]:
    parts = re.split(r"[、；;，,]", text)
    return [part.strip(" .。") for part in parts if part.strip(" .。")]


def clean_text(text: str) -> str:
    lines = normalize_lines(text)
    return "\n".join(lines)


def strip_markdown(text: str) -> str:
    text = text.replace("**", "")
    text = re.sub(r"^\-\s*", "", text, flags=re.M)
    return clean_text(text)


def first_sentence(text: str) -> str:
    line = clean_text(text).replace("\n", " ")
    return line.strip()


def parse_c1_beliefs(text: str) -> list[str]:
    beliefs: list[str] = []
    pattern = re.compile(r"^\d+\.\s*(.+?)(?:例子：.*)?$", re.M)
    for match in pattern.finditer(text):
        belief = match.group(1).strip().rstrip("。")
        if belief:
            beliefs.append(belief)
    return beliefs


def parse_qa_pairs(text: str) -> list[dict[str, str]]:
    pairs = []
    pattern = re.compile(
        r"(?:\d+\.\s*)?问[:：](.+?)\s*答[:：](.+?)(?=\n(?:\d+\.\s*)?问[:：]|\Z)",
        re.S,
    )
    for match in pattern.finditer(text):
        pairs.append(
            {
                "question": clean_text(match.group(1)),
                "answer": clean_text(match.group(2)),
            }
        )
    return pairs


def find_section(sections: dict[str, str], *aliases: str) -> str:
    for alias in aliases:
        if alias in sections:
            return sections[alias]
    normalized = {re.sub(r"\s+", "", key): value for key, value in sections.items()}
    for alias in aliases:
        compact = re.sub(r"\s+", "", alias)
        if compact in normalized:
            return normalized[compact]
    for key, value in sections.items():
        for alias in aliases:
            if alias in key or key in alias:
                return value
    return ""


def parse_colon_value(text: str, *labels: str) -> str:
    for line in normalize_lines(text):
        for label in labels:
            for sep in ("：", ":"):
                needle = f"{label}{sep}"
                if line.startswith(needle):
                    return line[len(needle) :].strip()
    return ""


def parse_markdown_list_after(label: str, text: str) -> list[str]:
    pattern = re.compile(
        rf"\*\*{re.escape(label)}：\*\*\s*\n(.*?)(?=\n\*\*|\Z)", re.S
    )
    match = pattern.search(text)
    if not match:
        return []
    return extract_list_values(match.group(1))


def parse_inline_bold_value(label: str, text: str) -> str:
    pattern = re.compile(rf"\*\*{re.escape(label)}：\*\*\s*(.+)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def parse_h2_body(title: str, text: str) -> str:
    sections = split_h2_sections(text)
    return sections.get(title, "").strip()


def parse_interview(interview_text: str) -> dict[str, Any]:
    sections = split_h3_sections(interview_text)
    a1 = clean_text(find_section(sections, "A1. 用 3 句话介绍自己", "自我介绍"))
    a2_map = extract_bullet_map(find_section(sections, "A2. 能力地图", "能力地图"))
    a3_map = extract_bullet_map(find_section(sections, "A3. 知识来源", "知识来源"))
    a4_map = extract_bullet_map(find_section(sections, "A4. 如何定义自己的工作价值", "工作价值"))
    b1_text = find_section(sections, "B1. 你如何分析一个新问题", "分析新问题")
    b2_map = extract_bullet_map(find_section(sections, "B2. 最常用的思维框架", "常用框架"))
    b3_text = find_section(sections, "B3. 如何处理信息不足", "信息不足时怎么办")
    b4_map = extract_bullet_map(find_section(sections, "B4. 最容易忽略的视角", "盲区"))
    c1_text = find_section(sections, "C1. 核心信念", "核心信念")
    c2_map = extract_bullet_map(find_section(sections, "C2. 优先级排序", "优先级排序"))
    c3_text = find_section(sections, "C3. 红线", "红线")
    c4_text = find_section(sections, "C4. 如何定义“好的建议”", "好建议")
    d1_text = find_section(sections, "D1. 口语化自我描述", "口语化描述")
    d2_map = extract_bullet_map(find_section(sections, "D2. 表达偏好", "表达偏好"))
    d3_map = extract_bullet_map(find_section(sections, "D3. 不喜欢的表达方式", "不喜欢的表达", "不喜欢的表达方式"))
    e1_text = find_section(sections, "E1. 3 个最常被问到的问题 + 真实回答", "常见问题")
    e3_text = find_section(sections, "E3. 完全不擅长的问题，你怎么回应（示范）", "不擅长的问题怎么回应")
    e4_text = find_section(sections, "E4. 一个解决过的复杂问题", "复杂问题案例")
    e1_pairs = parse_qa_pairs(e1_text)

    workflow_start = ""
    workflow_breakdown = ""
    workflow_decision_points: list[str] = []
    workflow_tools: list[str] = []
    workflow_delivery_review = ""

    if b1_text:
        b1_lines = normalize_lines(b1_text)
        if b1_lines:
            workflow_start = b1_lines[0]
        if len(b1_lines) > 1:
            workflow_breakdown = " -> ".join(b1_lines[1:])
    if e4_text:
        e4_map = extract_bullet_map(e4_text)
        workflow_start = workflow_start or e4_map.get("问题背景", "")
        if e4_map.get("我的分析过程"):
            workflow_breakdown = e4_map.get("我的分析过程", "")
        if e4_map.get("解决方案"):
            workflow_decision_points.append(e4_map.get("解决方案", ""))
        if e4_map.get("结果") or e4_map.get("如果重来会改变什么"):
            workflow_delivery_review = "；".join(
                item
                for item in [e4_map.get("结果", ""), e4_map.get("如果重来会改变什么", "")]
                if item
            )

    lower_text = interview_text.lower()
    if "python" in lower_text:
        workflow_tools.append("Python")
    if "评估" in interview_text:
        workflow_tools.append("评估集/失败样本分析")
    if "文档" in interview_text:
        workflow_tools.append("文档")
    if "代码" in interview_text:
        workflow_tools.append("代码库")

    source_materials = [
        {
            "id": "interview_a1",
            "type": "interview",
            "summary": "身份定位与核心价值",
            "reliability": "high",
        },
        {
            "id": "interview_c1",
            "type": "interview",
            "summary": "核心信念与真实决策例子",
            "reliability": "high",
        },
        {
            "id": "interview_e4",
            "type": "example_qa",
            "summary": "复杂问题处理方式",
            "reliability": "high",
        },
    ]

    knowledge_sources = []
    for key in ("主要影响我的书和作者", "长期关注的领域"):
        if key in a3_map:
            knowledge_sources.extend(split_cn_list(a3_map[key]))

    return {
        "meta": {
            "platform_target": "openclaw",
            "identity_confirmed": True,
        },
        "identity": {
            "summary": first_sentence(a1),
            "expertise": split_cn_list(a2_map.get("顶级能力", "")),
            "boundaries": dedupe_strings(
                [
                    value
                    for value in [
                        a2_map.get("边界"),
                        parse_colon_value(e3_text, "如果是品牌视觉或海报风格，我会直接说这不是我擅长的领域，但我可以先帮你把需求约束整理清楚"),
                    ]
                    if value
                ]
                + ([e3_text] if e3_text else [])
            ),
        },
        "mind_profile": {
            "core_beliefs": parse_c1_beliefs(c1_text),
            "thinking_style": clean_text(b1_text),
            "frameworks": list(b2_map.keys()),
            "blind_spots": [value for value in b4_map.values() if value],
            "decision_style": clean_text(c4_text),
            "priority_order": "；".join(
                f"{key}：{value}" for key, value in c2_map.items() if value
            ),
            "work_process": {
                "start": workflow_start,
                "breakdown": workflow_breakdown,
                "decision_points": dedupe_strings(workflow_decision_points),
                "tools": dedupe_strings(workflow_tools),
                "delivery_review": workflow_delivery_review,
            },
        },
        "expression": {
            "language_style": clean_text(d1_text),
            "response_format": "；".join(
                f"{key}：{value}" for key, value in d2_map.items() if value
            ),
            "avoid": [value for value in d3_map.values() if value],
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
        "runtime_candidates": {
            "common_questions": [item["question"] for item in e1_pairs if item.get("question")],
        },
        "knowledge_base": {
            "sources": knowledge_sources,
        },
        "source_materials": source_materials,
        "evidence_map": {
            "summary": ["interview_a1", "interview_a4"],
            "core_beliefs": ["interview_c1"],
            "boundaries": ["interview_a2", "interview_e3"],
            "common_questions": ["interview_e1"] if e1_pairs else [],
            "thinking_style": ["interview_b1", "interview_b2"] + (["interview_e4"] if e4_text else []),
        },
    }


def parse_mind_profile(text: str) -> dict[str, Any]:
    identity_summary = parse_h2_body("身份定位", text)
    expertise = parse_markdown_list_after("顶级能力", text)
    boundaries = parse_markdown_list_after("明确边界", text)
    frameworks = split_cn_list(parse_inline_bold_value("常用框架", text))
    blind_spots = split_cn_list(parse_inline_bold_value("已知盲区", text))
    core_beliefs = []
    for line in normalize_lines(parse_h2_body("核心信念", text)):
        line = re.sub(r"^\d+\.\s*", "", line)
        if line:
            core_beliefs.append(line)

    return {
        "identity": {
            "summary": first_sentence(identity_summary),
            "expertise": expertise,
            "boundaries": boundaries,
        },
        "mind_profile": {
            "core_beliefs": core_beliefs,
            "thinking_style": parse_inline_bold_value("分析习惯", text),
            "frameworks": frameworks,
            "blind_spots": blind_spots,
            "decision_style": strip_markdown(parse_h2_body("决策原则", text)),
            "priority_order": parse_inline_bold_value("优先级排序", text),
        },
        "expression": {
            "language_style": parse_inline_bold_value("语言特征", text),
            "response_format": parse_inline_bold_value("回答结构偏好", text),
            "avoid": split_cn_list(parse_inline_bold_value("避免的表达方式", text)),
        },
    }


def parse_system_prompt(text: str) -> tuple[str, int, dict[str, Any]]:
    score = 0
    score_match = re.search(r"质量评分：(\d+)/100", text)
    if score_match:
        score = int(score_match.group(1))
    sections = split_h2_sections(text)
    order = [
        "身份说明",
        "能力范围",
        "思维方式",
        "核心信念",
        "决策原则",
        "表达方式",
        "使用的工具",
        "重要约束",
    ]
    parts = []
    enabled_tools: dict[str, Any] = {
        "skills": {
            "universal": {
                "web_search": {"enabled": False, "use_case": ""},
                "code_execution": {"enabled": False, "languages": []},
                "data_analysis": {"enabled": False, "formats": []},
                "file_handling": {"enabled": False, "types": []},
            }
        }
    }
    tools_body = sections.get("使用的工具", "")
    for tool in extract_list_values(tools_body):
        key = tool.strip()
        if key in enabled_tools["skills"]["universal"]:
            enabled_tools["skills"]["universal"][key]["enabled"] = True

    for title in order:
        body = sections.get(title, "")
        if body:
            parts.append(strip_markdown(body))
    return "\n".join(parts).strip(), score, enabled_tools


def parse_research_digest(text: str) -> tuple[list[str], list[dict[str, str]], dict[str, list[str]]]:
    recommended_sources = extract_list_values(parse_h2_body("推荐资料来源", text))
    source_materials = []
    evidence_map: dict[str, list[str]] = {}
    if text.strip():
        source_materials.append(
            {
                "id": "research_digest_01",
                "type": "research",
                "summary": "职业共性、资料建议与评测场景",
                "reliability": "medium",
            }
        )
        evidence_map["evaluation_scenarios"] = ["research_digest_01"]
    return recommended_sources, source_materials, evidence_map


def parse_eval_report(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    total_match = re.search(r"## 总分：(\d+)/100", text)
    if total_match:
        result.setdefault("eval_summary", {})["overall_score"] = int(total_match.group(1))

    score_map = {
        "观点一致性": "consistency",
        "思维方式还原": "thinking_restoration",
        "语言风格相似度": "language_style",
        "边界意识": "boundary_awareness",
        "推理合理性": "reasoning",
    }
    for cn_name, key in score_map.items():
        match = re.search(rf"\|\s*{re.escape(cn_name)}\s*\|\s*(\d+)\s*\|", text)
        if match:
            result.setdefault("eval_summary", {})[key] = int(match.group(1))

    track_a = re.search(r"轨道 A.*?：(\d+)/100", text)
    track_b = re.search(r"轨道 B.*?：(\d+)/100", text)
    if track_a:
        result.setdefault("eval_summary", {})["consistency_track"] = int(track_a.group(1))
    if track_b:
        result.setdefault("eval_summary", {})["transfer_track"] = int(track_b.group(1))

    top_improvement = parse_h2_body("改进建议", text)
    priority_match = re.search(r"### 优先改进（影响最大）\n(.*?)(?=\n### |\Z)", top_improvement, re.S)
    if priority_match:
        result.setdefault("eval_summary", {})["top_improvement"] = clean_text(priority_match.group(1))
    return result


def derive_professional_skills(interview_text: str, research_text: str) -> list[dict[str, str]]:
    skills: list[dict[str, str]] = []

    if "RAG" in interview_text or "检索增强" in interview_text:
        skills.append(
            {
                "name": "RAG 架构建议",
                "trigger": "用户描述知识库问答、企业搜索或检索增强需求",
                "action": "先定义目标和评估标准，再按检索、切片、重排、生成链路给出方案",
            }
        )
    if "评估" in interview_text or "评估集" in interview_text:
        skills.append(
            {
                "name": "模型评估设计",
                "trigger": "用户需要定义 AI 效果验收标准或失败样本分析方法",
                "action": "设计样本集、评分维度、失败归因路径和上线验收方式",
            }
        )
    if "排障" in interview_text or "失败样本" in interview_text or "瓶颈" in interview_text:
        skills.append(
            {
                "name": "工程排障",
                "trigger": "线上 AI 系统回答不稳定、效果退化或引用异常",
                "action": "拆链路定位真实故障点，优先修数据、流程和评估闭环",
            }
        )
    if "复杂架构" in interview_text or "workflow" in interview_text or "多 agent" in interview_text:
        skills.append(
            {
                "name": "架构复杂度取舍",
                "trigger": "用户在简单工作流和复杂多代理方案之间犹豫",
                "action": "根据目标、约束、评估能力和维护成本判断是否值得上复杂架构",
            }
        )

    if not skills and research_text:
        common = extract_list_values(parse_h2_body("常见工作流", research_text))
        for idx, item in enumerate(common[:3], start=1):
            skills.append(
                {
                    "name": f"职业能力 {idx}",
                    "trigger": "用户询问该职业典型工作判断",
                    "action": item,
                }
            )
    return skills


def derive_confidence(data: dict[str, Any]) -> dict[str, int]:
    confidence = {
        "identity": 60,
        "capability_boundary": 60,
        "thinking_style": 60,
        "values": 60,
        "expression_style": 55,
    }
    if data.get("mind_profile", {}).get("frameworks"):
        confidence["thinking_style"] += 15
    if data.get("identity", {}).get("boundaries"):
        confidence["capability_boundary"] += 15
    if data.get("mind_profile", {}).get("core_beliefs"):
        confidence["values"] += 18
    if data.get("expression", {}).get("language_style"):
        confidence["expression_style"] += 12
    if data.get("system_prompt"):
        confidence["identity"] += 10
        confidence["thinking_style"] += 5
    if any(item.get("type") == "research" for item in data.get("source_materials", [])):
        confidence["capability_boundary"] += 5
    return {key: min(value, 95) for key, value in confidence.items()}


def summarize_trigger(trigger: str) -> str:
    text = clean_text(trigger).replace("用户", "").strip("：:，,。 ")
    if not text:
        return ""
    return text


def natural_use_case(text: str) -> str:
    text = clean_text(text).strip("：:，,。 ")
    if not text:
        return ""
    if text.startswith("用户"):
        return text
    if text.startswith(("需要", "想", "在", "做", "讨论", "分析", "排查", "定义", "搭")):
        return f"当用户{text}时"
    return f"当用户{ text }时"


def natural_boundary_case(boundary: str) -> str:
    text = clean_text(boundary).strip("：:，,。 ")
    if not text:
        return ""
    if text.startswith("不接受"):
        return f"当用户想让我接受{text[3:]}时"
    if text.startswith("不为"):
        return f"当用户希望我{text}时"
    if text.startswith("遇到"):
        body = text[2:]
        if "会明确转给" in body:
            left, _, _ = body.partition("会明确转给")
            left = left.strip("，,。 ")
            if left.endswith("类问题"):
                left = left[:-3] + "方面的专业判断"
            elif left.endswith("问题"):
                left = left[:-2] + "方面的问题处理"
            return f"当用户需要{left}时"
        return f"当问题{text}时"
    if text.startswith(("涉及", "属于", "需要", "询问")):
        return f"当问题{text}时"
    return f"当问题涉及{text}时"


def derive_runtime_config(data: dict[str, Any]) -> dict[str, Any]:
    meta = data.get("meta", {})
    identity = data.get("identity", {})
    runtime = data.get("runtime", {})
    skills = data.get("skills", {})
    candidates = data.get("runtime_candidates", {})

    profession = str(meta.get("profession", "")).strip()
    clone_name = str(meta.get("name", "")).strip() or "这个分身"
    expertise = identity.get("expertise", [])
    boundaries = identity.get("boundaries", [])
    if not isinstance(expertise, list):
        expertise = []
    if not isinstance(boundaries, list):
        boundaries = []

    professional = skills.get("professional", []) if isinstance(skills, dict) else []
    if not isinstance(professional, list):
        professional = []

    common_questions = candidates.get("common_questions", []) if isinstance(candidates, dict) else []
    if not isinstance(common_questions, list):
        common_questions = []

    use_cases = []
    if profession:
        use_cases.append(f"当用户想聊 {profession} 相关问题时")
    if expertise:
        use_cases.append(f"当用户需要 {'、'.join(expertise[:3])} 方向的建议时")
    for item in professional[:3]:
        if not isinstance(item, dict):
            continue
        trigger = summarize_trigger(str(item.get("trigger", "")).strip())
        if trigger:
            use_cases.append(natural_use_case(trigger))
    for question in common_questions[:2]:
        question = clean_text(question)
        if question:
            use_cases.append(f"当用户想讨论类似“{question}”这类问题时")
    use_cases.append(f"当用户想借 {clone_name} 的视角看一个问题时")

    do_not_use = ["当用户明确说“退出分身模式”或“我要和真正的AI说话”时"]
    for boundary in boundaries[:3]:
        do_not_use.append(natural_boundary_case(boundary))
    do_not_use.append(f"当用户询问 {clone_name} 的私人信息或实时动态时")

    runtime.setdefault("activation_mode", "always_on")
    runtime.setdefault("exit_commands", ["退出分身模式", "我要和真正的AI说话"])
    runtime["use_this_clone_when"] = dedupe_strings(use_cases)
    runtime["do_not_use_this_clone_when"] = dedupe_strings(do_not_use)
    runtime.setdefault("memory", {})
    runtime["memory"].setdefault(
        "remember",
        ["用户的核心问题和背景", "已经给出的建议，保持一致性", "用户对回答的反馈"],
    )
    runtime["memory"].setdefault(
        "forget",
        ["用户的私人信息（除非用户主动要求）", "超出能力边界的承诺"],
    )
    return runtime


def merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        elif value not in ({}, [], ""):
            base[key] = value
    return base


def dedupe_strings(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def dedupe_materials(values: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    result = []
    for item in values:
        key = item.get("id")
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def build_output(args: argparse.Namespace) -> dict[str, Any]:
    timestamp = args.timestamp or now_iso()
    interview_text = read_text(Path(args.interview))
    interview = parse_interview(interview_text)
    research_text = read_text(Path(args.research_digest)) if args.research_digest else ""

    data: dict[str, Any] = {
        "meta": {
            "name": args.name or "",
            "creator": args.creator or "",
            "profession": args.profession or "",
            "source_mode": "self_interview_plus_materials"
            if any([args.mind_profile, args.system_prompt, args.research_digest, args.eval_report])
            else "self_interview",
            "draft_status": "draft",
            "quality_score": args.quality_score or 0,
            "clone_type": "self",
        }
    }
    merge(data, interview)

    if args.mind_profile:
        merge(data, parse_mind_profile(read_text(Path(args.mind_profile))))

    if args.system_prompt:
        prompt, score, enabled_tools = parse_system_prompt(read_text(Path(args.system_prompt)))
        data["system_prompt"] = prompt
        merge(data, enabled_tools)
        data.setdefault("eval_summary", {})
        data["eval_summary"]["overall_score"] = args.quality_score or score
        data["meta"]["quality_score"] = args.quality_score or score

    if args.research_digest:
        sources, materials, evidence = parse_research_digest(research_text)
        data.setdefault("knowledge_base", {}).setdefault("sources", [])
        data["knowledge_base"]["sources"] = dedupe_strings(
            data["knowledge_base"]["sources"] + sources
        )
        data.setdefault("source_materials", [])
        data["source_materials"] = dedupe_materials(data["source_materials"] + materials)
        data.setdefault("evidence_map", {})
        for key, value in evidence.items():
            data["evidence_map"][key] = dedupe_strings(
                data["evidence_map"].get(key, []) + value
            )

    if args.eval_report:
        merge(data, parse_eval_report(read_text(Path(args.eval_report))))

    if args.consistency_track is not None or args.transfer_track is not None:
        eval_summary = data.setdefault("eval_summary", {})
        if args.consistency_track is not None:
            eval_summary["consistency_track"] = args.consistency_track
        if args.transfer_track is not None:
            eval_summary["transfer_track"] = args.transfer_track

    if args.overall_score is not None:
        data.setdefault("eval_summary", {})["overall_score"] = args.overall_score
        data["meta"]["quality_score"] = args.overall_score

    if args.top_improvement:
        data.setdefault("eval_summary", {})["top_improvement"] = args.top_improvement

    data.setdefault("skills", {})
    data["skills"]["professional"] = derive_professional_skills(interview_text, research_text)
    data["runtime"] = derive_runtime_config(data)

    data["confidence_by_dimension"] = derive_confidence(data)
    data.pop("runtime_candidates", None)
    data["update_log"] = [
        {
            "date": timestamp,
            "change": "Initial draft extraction",
            "reason": "Extracted from interview and optional supporting artifacts",
        }
    ]
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract clone-config draft JSON from interview markdown."
    )
    parser.add_argument("--interview", required=True, help="Path to interview_filled.md.")
    parser.add_argument("--output", required=True, help="Path to output JSON file.")
    parser.add_argument("--mind-profile", help="Optional path to mind_profile.md.")
    parser.add_argument("--system-prompt", help="Optional path to system_prompt.md.")
    parser.add_argument("--research-digest", help="Optional path to research_digest.md.")
    parser.add_argument("--eval-report", help="Optional path to eval_report.md.")
    parser.add_argument("--name", help="Clone name.")
    parser.add_argument("--creator", help="Creator name.")
    parser.add_argument("--profession", help="Profession.")
    parser.add_argument("--quality-score", type=int, help="Quality score override.")
    parser.add_argument("--overall-score", type=int, help="Overall evaluation score override.")
    parser.add_argument("--consistency-track", type=int, help="Consistency track score.")
    parser.add_argument("--transfer-track", type=int, help="Transfer track score.")
    parser.add_argument("--top-improvement", help="Top improvement suggestion.")
    parser.add_argument("--timestamp", help="Override timestamp in ISO-8601 format.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = build_output(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
