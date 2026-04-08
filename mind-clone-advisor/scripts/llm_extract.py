#!/usr/bin/env python3
"""Local per-article extraction into JSONL (no API keys required).

Uses domain_config.json for domain-specific keywords instead of hardcoded lists.
Run discover_domain.py first to generate the config.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from domain_config import (
    DECISION_PATTERNS,
    REASONING_PATTERNS,
    STANCE_PATTERNS,
    load_config,
)
from utils import extract_title, parse_date_from_filename, split_sentences, strip_front_matter, setup_logging

logger = setup_logging(__name__)


DEFAULT_MODEL_FALLBACK = [
    # Chinese generic model/framework terms
    "机会成本",
    "风险-收益权衡",
    "安全边际",
    "能力圈",
    "复利",
    "激励机制",
    "结构性变量",
    "反向思考",
    "供需",
    "长期主义",
    "周期",
    "杠杆",
    "利率",
    "流动性",
    "通胀",
    "估值",
    "博弈",
    "均值回归",
    # English generic model/framework terms
    "opportunity cost",
    "margin of safety",
    "circle of competence",
    "compounding",
    "incentives",
    "cycle",
    "leverage",
    "liquidity",
    "valuation",
    "mean reversion",
    "risk premium",
    "game theory",
    "network effect",
    "moat",
    "feedback loop",
    "second-order",
]

DEFAULT_VALUE_FALLBACK = [
    # Chinese
    "理性",
    "诚信",
    "长期主义",
    "纪律",
    "风险控制",
    "常识",
    "独立思考",
    "信念",
    "原则",
    # English
    "integrity",
    "discipline",
    "patience",
    "rational",
    "conviction",
    "humility",
    "transparency",
    "accountability",
    "trust",
]


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")



def score_sentences(sentences: list[str], terms: list[str]) -> list[tuple[int, str]]:
    scored = []
    for s in sentences:
        score = sum(s.count(k) for k in terms)
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def top_keywords(text: str, terms: list[str], top_k: int = 12) -> list[str]:
    counts = [(t, text.count(t)) for t in terms]
    counts = [c for c in counts if c[1] > 0]
    counts.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in counts[:top_k]]


def extract_stances(sentences: list[str]) -> list[str]:
    out = []
    for s in sentences:
        if any(p in s for p in STANCE_PATTERNS):
            out.append(s[:80])
    return list(dict.fromkeys(out))[:8]


def extract_reasoning(text: str) -> list[str]:
    found = []
    for label, pats in REASONING_PATTERNS.items():
        if any(p in text for p in pats):
            found.append(label)
    return found


def extract_models(text: str, model_keywords: list[str]) -> list[str]:
    return [k for k in model_keywords if k in text][:10]


def extract_values(text: str, value_keywords: list[str]) -> list[str]:
    return [k for k in value_keywords if k in text][:10]


def extract_decision_style(text: str) -> list[str]:
    styles = []
    for label, pats in DECISION_PATTERNS.items():
        if any(p in text for p in pats):
            styles.append(label)
    return styles


def language_fingerprint(
    text: str, terms: list[str], markers: list[str], top_k: int = 8
) -> list[str]:
    keywords = top_keywords(text, terms, top_k=top_k)
    extra = [k for k in markers if k in text]
    return list(dict.fromkeys(keywords + extra))[: top_k + 5]


def infer_blindspots(text: str, terms: list[str], theme_seeds: dict[str, list[str]] | None = None) -> list[str]:
    """Infer blindspots by detecting missing themes from domain_config.theme_seeds.

    If theme_seeds is provided, checks which theme groups have zero keyword hits
    in the text — these are likely blind spots. Falls back to term-frequency
    comparison when no theme_seeds are available.
    """
    if theme_seeds:
        bs = []
        for theme, keywords in theme_seeds.items():
            if not any(kw in text for kw in keywords):
                bs.append(f"未涉及「{theme}」相关主题")
                if len(bs) >= 5:
                    return bs
        return bs

    # Fallback: term-frequency based detection
    if not terms:
        return []
    counts = {t: text.count(t) for t in terms}
    high = [t for t, c in counts.items() if c >= 2]
    absent = [t for t, c in counts.items() if c == 0]
    bs = []
    for h in high[:3]:
        for a in absent[:3]:
            bs.append(f"频繁提及「{h}」但未涉及「{a}」")
            if len(bs) >= 5:
                return bs
    return bs


def clean_text(text: str, cleanup_patterns: list[str]) -> str:
    for pat in cleanup_patterns:
        text = text.replace(pat, "")
    return text


def is_bad_title(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return True
    bad = (
        "404",
        "not found",
        "page not found",
        "页面没有找到",
        "页面不存在",
        "证券时报官方网站-中国资本市场信息披露平台",
    )
    return any(x in t for x in bad)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="plain_text folder")
    parser.add_argument("--output", required=True, help="output jsonl path")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    terms = cfg["top_terms"]
    model_kw = list(dict.fromkeys(cfg["model_terms"] + DEFAULT_MODEL_FALLBACK))
    value_kw = list(dict.fromkeys(cfg["value_terms"] + DEFAULT_VALUE_FALLBACK))
    markers = cfg["language_markers"]
    cleanup = cfg["cleanup_patterns"]
    theme_seeds = cfg.get("theme_seeds", {})

    if not terms:
        logger.warning("[warn] no top_terms in config; run discover_domain.py first")

    input_dir = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if args.resume and output_path.exists():
        for line in output_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                obj = json.loads(line)
                existing.add(obj.get("source_file", ""))
            except Exception:
                continue

    files = sorted(input_dir.glob("*.md"))
    if args.limit:
        files = files[: args.limit]

    for path in files:
        if path.name in existing:
            continue
        text = load_text(path)
        text = strip_front_matter(text)
        title = extract_title(text)
        date = parse_date_from_filename(path.name) or ""
        if is_bad_title(title):
            logger.info("[skip] bad title: %s", path.name)
            continue

        body = text
        if title:
            body = text.replace(title, "", 1).strip()
        body = clean_text(body, cleanup)
        if len(body.strip()) < 120:
            logger.info("[skip] too short after cleanup: %s", path.name)
            continue

        sentences = split_sentences(body)
        core_candidates = score_sentences(sentences, terms)
        core_view = (
            "。".join([s for _, s in core_candidates[:2]]) if core_candidates else ""
        )

        obj = {
            "source_file": path.name,
            "title": title,
            "date": date,
            "core_view": core_view,
            "stances": extract_stances(sentences),
            "reasoning": extract_reasoning(body),
            "models": extract_models(body, model_kw),
            "values": extract_values(body, value_kw),
            "decision_style": extract_decision_style(body),
            "language_fingerprint": language_fingerprint(body, terms, markers),
            "blindspots": infer_blindspots(body, terms, theme_seeds=theme_seeds),
            "keywords": top_keywords(body, terms, top_k=12),
        }

        with output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    logger.info(f"[done] output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
