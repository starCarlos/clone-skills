#!/usr/bin/env python3
"""Automated evaluation of a person skill against evaluation_plan.md.

This evaluator is intentionally heuristic, but it is built around the actual
artifacts the skill produces:
  - thinking_profile.md
  - system_prompt.md
  - evidence_anchors.md
  - analysis/extractions.jsonl

It scores each question along six dimensions and reports which sections,
extractions, and anchors were relevant, instead of relying on naive token
overlap between the question text and raw extraction fields.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from utils import load_jsonl, setup_logging, strip_front_matter

logger = setup_logging(__name__)

REPORT_SCOPE_NOTE = (
    "This report scores artifact coverage, not live response quality. "
    "It evaluates whether the skill artifacts contain enough structured support "
    "for the tested questions."
)

QUESTION_STOP_TERMS = {
    "这个",
    "那个",
    "该角",
    "角色",
    "如何",
    "怎么",
    "什么",
    "是否",
    "哪里",
    "哪种",
    "怎样",
    "会如何",
    "问题",
    "要求",
    "至少",
    "相关",
    "原文",
    "角色最",
    "最核心",
}

BOUNDARY_MARKERS = [
    "能力圈",
    "边界",
    "约束",
    "不确定",
    "信息缺口",
    "超出",
    "不擅长",
    "无法判断",
    "不足以",
    "拒绝",
    "保守",
    "失效条件",
    "constraint",
    "boundary",
    "limitation",
]

STYLE_MARKERS = [
    "语言",
    "风格",
    "表达",
    "句式",
    "口语",
    "结论先行",
    "分点",
    "口头禅",
    "语言指纹",
]

FRAMEWORK_MARKERS = [
    "框架",
    "模型",
    "思维",
    "推理",
    "逻辑",
    "分析顺序",
    "思考流程",
    "判断路径",
    "第二层思维",
    "second-level",
    "cycle",
    "pendulum",
    "护城河",
    "安全边际",
]

CONCEPT_HINTS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (
        ("框架", "模型", "思维", "推理", "路径", "逻辑", "分析顺序"),
        (
            "框架",
            "模型",
            "心智模型",
            "核心信念",
            "思维特征",
            "思维方式",
            "分析顺序",
            "思考流程",
            "第二层思维",
            "周期",
            "钟摆",
            "护城河",
            "安全边际",
        ),
    ),
    (
        ("风险", "边界", "能力圈", "不确定", "信息缺口", "证据不足", "超出"),
        (
            "风险",
            "边界",
            "能力圈",
            "约束",
            "不确定",
            "信息缺口",
            "保守",
            "拒绝",
            "降级",
            "失效条件",
        ),
    ),
    (
        ("风格", "表达", "语气", "语言", "口头禅", "句式"),
        (
            "语言",
            "风格",
            "表达",
            "语言指纹",
            "句式",
            "结论先行",
            "分点",
            "口语化",
        ),
    ),
    (
        ("长期", "短期", "周期", "时间"),
        ("长期", "短期", "周期", "时间偏好", "复利", "耐心"),
    ),
    (
        ("优先", "排序", "先做什么", "取舍"),
        ("优先", "排序", "价值排序", "取舍", "动作建议", "先", "后"),
    ),
    (
        ("原文", "锚点", "证据", "引用", "观点"),
        ("原文", "锚点", "证据", "引用", "来源", "观点", "evidence"),
    ),
    (
        ("推演", "延伸", "反证", "冲突", "一致性"),
        ("推演", "延伸", "反证", "一致性", "矛盾", "假设", "情境", "失效条件"),
    ),
]


def normalize_text(text: str) -> str:
    text = text or ""
    text = strip_front_matter(text)
    text = text.replace("—", "-").replace("–", "-").replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def extract_question_terms(text: str) -> set[str]:
    terms: set[str] = set()
    normalized = normalize_text(text)
    for word in re.findall(r"[a-z]{3,}", normalized):
        terms.add(word)

    for chunk in re.findall(r"[\u4e00-\u9fff]+", text):
        if 2 <= len(chunk) <= 10 and chunk not in QUESTION_STOP_TERMS:
            terms.add(chunk)
        max_n = min(len(chunk), 4)
        for n in range(2, max_n + 1):
            for i in range(len(chunk) - n + 1):
                frag = chunk[i : i + n]
                if frag in QUESTION_STOP_TERMS:
                    continue
                if all(ch in "这个那个什么如何怎么是否会该最" for ch in frag):
                    continue
                terms.add(frag)
    return {term for term in terms if len(term) >= 2}


def split_hint_values(text: str) -> list[str]:
    parts = re.split(r"[、，,/；;]\s*|\s{2,}", text)
    return [part.strip() for part in parts if part.strip()]


def parse_eval_plan(text: str) -> list[dict]:
    """Extract test questions and optional metadata from evaluation_plan.md."""
    questions: list[dict] = []
    current_category = ""
    current: dict | None = None

    def flush_current() -> None:
        nonlocal current
        if current:
            deduped = []
            seen = set()
            for cue in current["cues"]:
                if cue in seen:
                    continue
                seen.add(cue)
                deduped.append(cue)
            current["cues"] = deduped
            questions.append(current)
            current = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if re.match(r"^#{1,3}\s.*A 类", line) or "有据可查" in line:
            flush_current()
            current_category = "A"
            continue
        if re.match(r"^#{1,3}\s.*B 类", line) or "推理延伸" in line:
            flush_current()
            current_category = "B"
            continue
        if re.match(r"^#{1,3}\s.*C 类", line) or "边界测试" in line:
            flush_current()
            current_category = "C"
            continue

        match = re.match(r"^\d+[.)、]\s*(.+)", line)
        if match and current_category:
            flush_current()
            current = {
                "category": current_category,
                "question": match.group(1).strip().strip('"'),
                "cues": [],
                "anchor_requirement": 0,
            }
            continue

        if current and line.startswith(("- ", "* ")):
            body = line[2:].strip()
            if "：" in body:
                key, value = body.split("：", 1)
                key = key.strip()
                value = value.strip()
                if key in {"关注信号", "关键词", "检查点"}:
                    current["cues"].extend(split_hint_values(value))
                    continue
                if key == "锚点要求":
                    current["cues"].extend(split_hint_values(value))
                    number = re.search(r"(\d+)", value)
                    if number:
                        current["anchor_requirement"] = int(number.group(1))
                    continue
            if body.endswith(("？", "?")) and current_category:
                flush_current()
                current = {
                    "category": current_category,
                    "question": body,
                    "cues": [],
                    "anchor_requirement": 0,
                }

    flush_current()
    return questions


def split_markdown_sections(text: str, kind: str) -> list[dict]:
    docs: list[dict] = []
    current_title = f"{kind}-overview"
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        content = "\n".join(buffer).strip()
        if not content:
            return
        docs.append(
            {
                "kind": kind,
                "label": current_title,
                "label_norm": normalize_text(current_title),
                "text": content,
                "text_norm": normalize_text(content),
                "anchor_count": 0,
                "model_count": 0,
                "reasoning_count": 0,
                "value_count": 0,
                "style_count": sum(1 for marker in STYLE_MARKERS if marker in content),
                "boundary_count": sum(1 for marker in BOUNDARY_MARKERS if marker in content),
            }
        )

    for raw_line in strip_front_matter(text).splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            flush()
            current_title = re.sub(r"^#+\s*", "", stripped)
            buffer = []
            continue
        buffer.append(stripped)
    flush()
    return docs


def parse_anchor_docs(text: str) -> list[dict]:
    docs: list[dict] = []
    for line in text.splitlines():
        match = re.match(r'^\d+\.\s+([^|]+)\|\s*([^|]+)\|\s*"(.+)"\s*$', line.strip())
        if not match:
            continue
        date = match.group(1).strip()
        source = match.group(2).strip()
        anchor_text = match.group(3).strip()
        label = f"{date} | {source}"
        docs.append(
            {
                "kind": "anchor",
                "label": label,
                "label_norm": normalize_text(label),
                "text": anchor_text,
                "text_norm": normalize_text(anchor_text),
                "anchor_count": 1,
                "model_count": 0,
                "reasoning_count": 0,
                "value_count": 0,
                "style_count": 0,
                "boundary_count": 0,
            }
        )
    return docs


def extraction_doc(item: dict) -> dict:
    anchors = item.get("evidence_anchors") or []
    anchor_text = " ".join(anchor.get("text", "") for anchor in anchors if anchor.get("text"))
    joined_parts = [
        item.get("title", ""),
        item.get("core_view", ""),
        " ".join(item.get("stances", []) or []),
        " ".join(item.get("keywords", []) or []),
        " ".join(item.get("models", []) or []),
        " ".join(item.get("values", []) or []),
        " ".join(item.get("reasoning", []) or []),
        " ".join(item.get("decision_style", []) or []),
        " ".join(item.get("language_fingerprint", []) or []),
        " ".join(item.get("blindspots", []) or []),
        anchor_text,
    ]
    text = " ".join(part for part in joined_parts if part)
    label = item.get("title") or item.get("source_file") or "extraction"
    return {
        "kind": "extraction",
        "label": label,
        "label_norm": normalize_text(label),
        "text": text,
        "text_norm": normalize_text(text),
        "anchor_count": len(anchors),
        "model_count": len(item.get("models", []) or []),
        "reasoning_count": len(item.get("reasoning", []) or []),
        "value_count": len(item.get("values", []) or []),
        "style_count": len(item.get("language_fingerprint", []) or []),
        "boundary_count": len(item.get("blindspots", []) or []),
    }


def build_reference_docs(
    skill_dir: Path,
    items: list[dict],
    profile_text: str,
    prompt_text: str,
) -> list[dict]:
    docs: list[dict] = []
    docs.extend(split_markdown_sections(profile_text, "profile"))
    docs.extend(split_markdown_sections(prompt_text, "prompt"))
    docs.extend(extraction_doc(item) for item in items)

    anchor_path = skill_dir / "evidence_anchors.md"
    if anchor_path.exists():
        docs.extend(parse_anchor_docs(anchor_path.read_text(encoding="utf-8", errors="ignore")))
    return docs


def classify_question(question: str, category: str, cues: list[str]) -> dict[str, bool]:
    text = normalize_text(" ".join([question, *cues]))

    def has_any(terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

    return {
        "framework": has_any(("框架", "模型", "思维", "推理", "逻辑", "路径", "分析顺序")),
        "boundary": category == "C"
        or has_any(("边界", "能力圈", "信息缺口", "不确定", "风险", "拒绝", "超出")),
        "style": has_any(("风格", "表达", "语气", "语言", "句式")),
        "priority": has_any(("优先", "排序", "先做什么", "取舍")),
        "time": has_any(("长期", "短期", "周期", "时间")),
        "evidence": has_any(("原文", "锚点", "证据", "引用", "观点")),
        "extension": category == "B"
        or has_any(("推演", "延伸", "反证", "冲突", "一致性", "假设")),
    }


def expand_query_terms(question: str, category: str, cues: list[str]) -> set[str]:
    terms = extract_question_terms(question)
    cue_text = " ".join(cues)
    terms.update(extract_question_terms(cue_text))
    combined = f"{question} {cue_text}"
    for triggers, expansions in CONCEPT_HINTS:
        if any(trigger in combined for trigger in triggers):
            terms.update(expansions)
    if category == "C":
        terms.update({"边界", "能力圈", "不确定", "信息缺口", "拒绝", "风险"})
    return {term.lower() for term in terms if len(term) >= 2}


def score_doc(doc: dict, query_terms: set[str], flags: dict[str, bool]) -> tuple[int, list[str]]:
    score = 0
    matched: list[str] = []
    label = doc["label_norm"]
    text = doc["text_norm"]

    for term in sorted(query_terms):
        if term in label:
            score += 5
            matched.append(term)
            continue
        if term in text:
            score += 3
            matched.append(term)

    if flags["framework"]:
        if doc["kind"] in {"profile", "prompt"} and any(marker in text or marker in label for marker in FRAMEWORK_MARKERS):
            score += 8
        if doc["kind"] == "extraction" and (doc["model_count"] > 0 or doc["reasoning_count"] > 0):
            score += 6

    if flags["boundary"]:
        if doc["kind"] in {"profile", "prompt"} and any(marker in text or marker in label for marker in BOUNDARY_MARKERS):
            score += 8
        if doc["kind"] == "extraction" and doc["boundary_count"] > 0:
            score += 5

    if flags["style"]:
        if doc["kind"] in {"profile", "prompt"} and any(marker in text or marker in label for marker in STYLE_MARKERS):
            score += 8
        if doc["kind"] == "extraction" and doc["style_count"] > 0:
            score += 5

    if flags["priority"] and ("排序" in text or "价值排序" in text or doc["value_count"] > 0):
        score += 5

    if flags["time"] and ("长期" in text or "短期" in text or "周期" in text or "time" in text):
        score += 4

    if flags["evidence"] and doc["kind"] == "anchor":
        score += 8

    if flags["extension"] and doc["kind"] == "extraction" and doc["reasoning_count"] > 0:
        score += 4

    if doc["kind"] == "anchor":
        score += 1
    if doc["kind"] == "extraction" and doc["anchor_count"] > 0:
        score += min(doc["anchor_count"], 2)

    return score, matched


def search_supporting_docs(
    docs: list[dict],
    query_terms: set[str],
    flags: dict[str, bool],
) -> list[dict]:
    scored = []
    for doc in docs:
        score, matched = score_doc(doc, query_terms, flags)
        if score <= 0:
            continue
        scored.append(
            {
                "score": score,
                "matched_terms": matched,
                "doc": doc,
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)

    selected: list[dict] = []
    kind_counts: dict[str, int] = {}
    kind_limits = {"profile": 3, "prompt": 3, "extraction": 4, "anchor": 3}
    for hit in scored:
        kind = hit["doc"]["kind"]
        if kind_counts.get(kind, 0) >= kind_limits.get(kind, 2):
            continue
        selected.append(hit)
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        if len(selected) >= 10:
            break
    return selected


def score_from_thresholds(value: int, thresholds: tuple[int, int, int, int]) -> int:
    high, mid_high, mid_low, low = thresholds
    if value >= high:
        return 5
    if value >= mid_high:
        return 4
    if value >= mid_low:
        return 3
    if value >= low:
        return 2
    return 1


def score_question(question: dict, docs: list[dict]) -> dict:
    flags = classify_question(question["question"], question["category"], question["cues"])
    query_terms = expand_query_terms(question["question"], question["category"], question["cues"])
    hits = search_supporting_docs(docs, query_terms, flags)

    profile_hits = [hit for hit in hits if hit["doc"]["kind"] == "profile"]
    prompt_hits = [hit for hit in hits if hit["doc"]["kind"] == "prompt"]
    extraction_hits = [hit for hit in hits if hit["doc"]["kind"] == "extraction"]
    anchor_hits = [hit for hit in hits if hit["doc"]["kind"] == "anchor"]

    anchor_support = len(anchor_hits) + sum(1 for hit in extraction_hits if hit["doc"]["anchor_count"] > 0)
    structure_support = len(profile_hits) + len(prompt_hits)
    model_support = sum(
        1
        for hit in hits
        if hit["doc"]["model_count"] > 0
        or hit["doc"]["reasoning_count"] > 0
        or any(marker in hit["doc"]["label"] for marker in ("模型", "框架", "思维", "流程"))
    )
    value_support = sum(
        1
        for hit in hits
        if hit["doc"]["value_count"] > 0 or any(marker in hit["doc"]["label"] for marker in ("信念", "价值", "排序"))
    )
    style_support = sum(
        1
        for hit in hits
        if hit["doc"]["style_count"] > 0 or any(marker in hit["doc"]["label"] for marker in ("语言", "风格", "表达"))
    )
    boundary_support = sum(
        1
        for hit in hits
        if hit["doc"]["boundary_count"] > 0 or any(marker in hit["doc"]["text"] for marker in BOUNDARY_MARKERS)
    )
    reasoning_support = sum(
        1
        for hit in hits
        if hit["doc"]["reasoning_count"] > 0
        or any(marker in hit["doc"]["label"] for marker in ("思考流程", "分析顺序", "失效条件", "反证"))
    )

    scores: dict[str, int] = {}
    notes: list[str] = []

    anchor_requirement = question.get("anchor_requirement", 0)
    if anchor_requirement > 0 and anchor_support < anchor_requirement:
        notes.append(f"原文锚点不足，要求 {anchor_requirement} 条，命中 {anchor_support} 条")
    if not hits:
        notes.append("未找到足够的结构化支持材料")

    if anchor_support >= max(anchor_requirement, 2):
        scores["证据锚定"] = 5
    elif anchor_support >= max(anchor_requirement, 1):
        scores["证据锚定"] = 4
    elif len(extraction_hits) >= 2 or len(anchor_hits) >= 1:
        scores["证据锚定"] = 3
    elif structure_support > 0:
        scores["证据锚定"] = 2
    else:
        scores["证据锚定"] = 1

    scores["观点一致性"] = score_from_thresholds(structure_support + value_support, (5, 3, 2, 1))
    scores["思维模式"] = score_from_thresholds(model_support, (4, 3, 2, 1))
    scores["语言风格"] = score_from_thresholds(style_support, (3, 2, 1, 1))
    scores["推理合理性"] = score_from_thresholds(reasoning_support + len(extraction_hits), (5, 3, 2, 1))
    scores["边界意识"] = score_from_thresholds(
        boundary_support + (1 if question["category"] == "C" else 0),
        (4, 3, 2, 1),
    )

    if scores["边界意识"] <= 2:
        notes.append("边界声明偏弱")
    if scores["思维模式"] <= 2:
        notes.append("推理框架支撑不足")

    total = sum(scores.values())
    max_total = len(scores) * 5

    matched_sections = [
        hit["doc"]["label"]
        for hit in hits
        if hit["doc"]["kind"] in {"profile", "prompt"}
    ][:6]
    matched_extractions = [
        hit["doc"]["label"]
        for hit in extraction_hits
    ][:4]
    matched_anchors = [
        hit["doc"]["label"]
        for hit in anchor_hits
    ][:3]

    return {
        "question": question["question"],
        "category": question["category"],
        "scores": scores,
        "total": total,
        "max": max_total,
        "evidence_count": len(extraction_hits) + len(anchor_hits),
        "anchor_count": anchor_support,
        "matched_sections": matched_sections,
        "matched_extractions": matched_extractions,
        "matched_anchors": matched_anchors,
        "query_terms": sorted(query_terms)[:20],
        "notes": notes,
    }


def generate_report(skill_name: str, results: list[dict]) -> str:
    lines = [
        f"# Artifact Coverage Report: {skill_name}",
        "",
        REPORT_SCOPE_NOTE,
        "",
        "Evaluation mode: artifact_coverage",
        "",
    ]

    total_score = sum(result["total"] for result in results)
    total_max = sum(result["max"] for result in results)
    pct = (total_score / total_max * 100) if total_max > 0 else 0
    lines.append(f"Overall Score: **{total_score}/{total_max}** ({pct:.0f}%)")
    lines.append("")

    dimension_totals: dict[str, list[int]] = {}
    for result in results:
        for dimension, score in result["scores"].items():
            dimension_totals.setdefault(dimension, []).append(score)

    lines.append("## Dimension Averages")
    lines.append("")
    for dimension, scores in dimension_totals.items():
        average = sum(scores) / len(scores) if scores else 0
        lines.append(f"- {dimension}: {average:.1f}/5")
    lines.append("")

    for category, category_label in [("A", "有据可查"), ("B", "推理延伸"), ("C", "边界测试")]:
        category_results = [result for result in results if result["category"] == category]
        if not category_results:
            continue
        cat_total = sum(result["total"] for result in category_results)
        cat_max = sum(result["max"] for result in category_results)
        cat_pct = (cat_total / cat_max * 100) if cat_max > 0 else 0
        lines.append(f"## {category} 类: {category_label} ({cat_pct:.0f}%)")
        lines.append("")
        for result in category_results:
            q_pct = (result["total"] / result["max"] * 100) if result["max"] > 0 else 0
            lines.append(f"### Q: {result['question']}")
            lines.append("")
            lines.append(f"- Score: {result['total']}/{result['max']} ({q_pct:.0f}%)")
            lines.append(f"- Evidence items: {result['evidence_count']}, Anchors: {result['anchor_count']}")
            if result["matched_sections"]:
                lines.append(f"- Matched sections: {'; '.join(result['matched_sections'])}")
            if result["matched_extractions"]:
                lines.append(f"- Matched extractions: {'; '.join(result['matched_extractions'])}")
            if result["matched_anchors"]:
                lines.append(f"- Matched anchors: {'; '.join(result['matched_anchors'])}")
            for dimension, score in result["scores"].items():
                lines.append(f"  - {dimension}: {score}/5")
            if result["notes"]:
                lines.append(f"- Notes: {'; '.join(result['notes'])}")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a person skill.")
    parser.add_argument("--skill-dir", required=True, help="person skill directory")
    parser.add_argument("--plan", default="", help="evaluation_plan.md path (optional)")
    parser.add_argument("--out", default="", help="output evaluation_report.md path")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    if not skill_dir.exists():
        raise SystemExit(f"skill directory not found: {skill_dir}")

    plan_path = Path(args.plan) if args.plan else skill_dir / "evaluation_plan.md"
    if not plan_path.exists():
        raise SystemExit(f"evaluation plan not found: {plan_path}")

    plan_text = plan_path.read_text(encoding="utf-8", errors="ignore")
    questions = parse_eval_plan(plan_text)
    if not questions:
        raise SystemExit("no test questions found in evaluation plan")
    logger.info("[info] parsed %d test questions from %s", len(questions), plan_path.name)

    ext_path = skill_dir / "analysis" / "extractions.jsonl"
    items = load_jsonl(ext_path) if ext_path.exists() else []

    profile_path = skill_dir / "thinking_profile.md"
    profile_text = profile_path.read_text(encoding="utf-8", errors="ignore") if profile_path.exists() else ""

    prompt_path = skill_dir / "system_prompt.md"
    prompt_text = prompt_path.read_text(encoding="utf-8", errors="ignore") if prompt_path.exists() else ""

    docs = build_reference_docs(skill_dir, items, profile_text, prompt_text)
    results = [score_question(question, docs) for question in questions]

    report = generate_report(skill_dir.name, results)
    out_path = Path(args.out) if args.out else skill_dir / "evaluation_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    logger.info("[done] evaluation report written to %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
