#!/usr/bin/env python3
"""Build classification labels for each article in plain_text.

Generates labels.jsonl with per-article metadata:
  - theme: matched from domain_config theme_seeds
  - content_type: inferred from keywords (观点输出/案例分析/方法论/访谈/演讲)
  - reliability: inferred from metadata/filename patterns (原文/转述/编辑整理)
  - time_period: extracted from date prefix
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from domain_config import load_config
from utils import (
    extract_title,
    load_jsonl,
    parse_date_from_filename,
    setup_logging,
    strip_front_matter,
    write_jsonl,
)

logger = setup_logging(__name__)

# ---------------------------------------------------------------------------
# Content type detection
# ---------------------------------------------------------------------------

CONTENT_TYPE_PATTERNS: dict[str, list[str]] = {
    "观点输出": [
        "我认为", "我觉得", "核心是", "本质是", "关键是",
        "I believe", "I think", "my view", "the key is", "the point is",
    ],
    "案例分析": [
        "案例", "实例", "案例分析", "复盘", "回顾",
        "case study", "case analysis", "post-mortem", "retrospective",
    ],
    "方法论": [
        "方法", "步骤", "流程", "框架", "如何", "指南",
        "how to", "step by step", "framework", "methodology", "guide",
    ],
    "访谈": [
        "访谈", "采访", "对话", "问答", "Q:", "A:", "问：", "答：",
        "interview", "conversation", "Q&A",
    ],
    "演讲": [
        "演讲", "讲话", "致辞", "开幕", "闭幕", "大会",
        "speech", "talk", "address", "keynote", "lecture", "commencement",
    ],
}

RELIABILITY_PATTERNS: dict[str, list[str]] = {
    "原文": [
        "shareholder letter", "annual letter", "owner", "memo",
        "致股东", "股东信", "备忘录", "亲笔", "原文",
    ],
    "转述": [
        "转载", "转述", "据说", "reported", "according to", "paraphrased",
    ],
    "编辑整理": [
        "整理", "编辑", "摘要", "要点", "总结", "compiled", "edited", "summary",
    ],
}


def detect_content_type(text: str) -> str:
    """Return the best-matching content type label."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for label, patterns in CONTENT_TYPE_PATTERNS.items():
        count = sum(1 for p in patterns if p.lower() in text_lower)
        if count > 0:
            scores[label] = count
    if scores:
        return max(scores, key=scores.get)
    return "观点输出"


def detect_reliability(text: str, filename: str) -> str:
    """Return a reliability label based on text content and filename."""
    combined = (text + " " + filename).lower()
    scores: dict[str, int] = {}
    for label, patterns in RELIABILITY_PATTERNS.items():
        count = sum(1 for p in patterns if p.lower() in combined)
        if count > 0:
            scores[label] = count
    if scores:
        return max(scores, key=scores.get)
    return "原文"


def detect_time_period(date_str: str | None) -> str:
    """Return a time period label from a date string like 2020-03."""
    if not date_str:
        return "未知"
    m = re.match(r"(\d{4})", date_str)
    if not m:
        return "未知"
    year = int(m.group(1))
    if year < 1990:
        return "早期"
    if year < 2000:
        return "1990年代"
    if year < 2010:
        return "2000年代"
    if year < 2020:
        return "2010年代"
    return "2020年代"


def match_theme(text: str, theme_seeds: dict[str, list[str]]) -> str:
    """Return the best-matching theme from theme_seeds."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for theme, seeds in theme_seeds.items():
        count = sum(1 for s in seeds if s.lower() in text_lower)
        if count > 0:
            scores[theme] = count
    if scores:
        return max(scores, key=scores.get)
    return "其他"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build classification labels for articles.")
    parser.add_argument("--plain-text-dir", required=True, help="plain_text folder")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--out", required=True, help="output labels.jsonl path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    theme_seeds = cfg.get("theme_seeds", {})

    plain_dir = Path(args.plain_text_dir)
    paths = sorted(plain_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"no .md files found in {plain_dir}")

    labels: list[dict] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        body = strip_front_matter(text)
        title = extract_title(body)
        date = parse_date_from_filename(path.name)

        label = {
            "file": path.name,
            "title": title,
            "date": date or "",
            "theme": match_theme(body, theme_seeds),
            "content_type": detect_content_type(body),
            "reliability": detect_reliability(body, path.name),
            "time_period": detect_time_period(date),
        }
        labels.append(label)

    out_path = Path(args.out)
    write_jsonl(out_path, labels)
    logger.info("[done] labels=%d out=%s", len(labels), out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
