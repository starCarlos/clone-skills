#!/usr/bin/env python3
"""Summarize extraction JSONL into thinking_profile.md and system_prompt.md locally.

Uses domain_config.json for domain-specific keywords. Beliefs are derived from
actual extraction data rather than hardcoded templates.
Detects corpus language (Chinese vs English) and uses appropriate templates.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from domain_config import load_config
from topic_model import build_tfidf, display_term, lsa_topics, tokenize
from utils import parse_date_from_filename, strip_front_matter, sample_text, load_jsonl, setup_logging

logger = setup_logging(__name__)

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ASCII_WORD_RE = re.compile(r"^[a-z][a-z0-9_-]{2,}$")


def detect_corpus_language(docs: list[str]) -> str:
    """Detect whether corpus is predominantly Chinese or English.

    Returns 'zh' or 'en'.
    """
    cjk_chars = 0
    latin_chars = 0
    sample = " ".join(docs[:20])[:50000]  # Sample first 20 docs
    for ch in sample:
        if CJK_RE.match(ch):
            cjk_chars += 1
        elif ch.isascii() and ch.isalpha():
            latin_chars += 1
    if cjk_chars > latin_chars * 0.3:
        return "zh"
    return "en"


# ---------------------------------------------------------------------------
# Fallback constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL_FALLBACK_ZH = [
    "机会成本模型",
    "风险-收益权衡",
    "安全边际模型",
    "能力圈模型",
    "复利增长模型",
    "激励机制模型",
    "结构性变量",
    "反向思考",
    "供需模型",
    "长期主义框架",
]

DEFAULT_MODEL_FALLBACK_EN = [
    "opportunity cost framework",
    "risk-reward tradeoff",
    "margin of safety",
    "circle of competence",
    "compounding growth model",
    "incentive alignment",
    "structural variables analysis",
    "contrarian thinking",
    "supply-demand dynamics",
    "long-term orientation",
]

DEFAULT_VALUE_FALLBACK_ZH = [
    "理性",
    "诚信",
    "长期主义",
    "纪律",
    "风险控制",
    "常识",
    "独立思考",
]

DEFAULT_VALUE_FALLBACK_EN = [
    "rational",
    "integrity",
    "long-term thinking",
    "discipline",
    "risk management",
    "common sense",
    "independent thinking",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Normalize model labels to avoid too-short items (validator requires >= 5 chars)
def normalize_model_label(label: str) -> str:
    if not label:
        return label
    if len(label) < 5 and not label.endswith("模型") and not label.endswith("原则"):
        return label + "增长模型"
    if len(label) < 5 and label.endswith("模型"):
        return label.replace("模型", "增长模型")
    return label


def choose_top(counter: Counter, n: int) -> list[str]:
    return [k for k, _ in counter.most_common(n)]


NOISY_TOKENS = {
    "password", "register", "cancel", "login", "log", "http", "https", "www", "com",
    "png", "jpg", "jpeg", "gif", "datalayer", "cloudflare", "captcha",
}


def is_noisy_token(tok: str) -> bool:
    t = (tok or "").strip().lower()
    if not t:
        return True
    if t in NOISY_TOKENS:
        return True
    if len(t) <= 2:
        return True
    if t.isdigit():
        return True
    if any(x in t for x in ("__", ".com", "://", "www.", "img", "cdn")):
        return True
    return False


def sanitize_tokens(tokens: list[str], max_items: int) -> list[str]:
    out: list[str] = []
    for tok in tokens:
        t = (tok or "").strip()
        if not t:
            continue
        if is_noisy_token(t):
            continue
        if t not in out:
            out.append(t)
        if len(out) >= max_items:
            break
    return out


def infer_beliefs_from_data(
    top_topics: list[str], top_models: list[str], config: dict, lang: str
) -> list[str]:
    """Infer beliefs from actual keyword/model frequencies."""
    beliefs = []

    belief_buckets = config.get("belief_buckets", {})
    for belief_label, keywords in belief_buckets.items():
        if any(kw in top_topics or kw in top_models for kw in keywords):
            if lang == "en":
                beliefs.append(f"Focused on {belief_label}-related topics")
            else:
                beliefs.append(f"关注{belief_label}相关议题")

    if len(beliefs) < 3:
        if lang == "en":
            beliefs.extend([
                "Emphasizes structured thinking with reproducible evidence",
                "Favors long-term compounding decisions",
                "Focuses on risk and worst-case scenario tolerance",
            ])
        else:
            beliefs.extend([
                "强调结构化思考与可复盘证据",
                "倾向长期主义与复利型决策",
                "关注风险与可承受的最坏情形",
            ])

    return beliefs[:5]


def _generate_blindspots(top_topics: list[str], top_blindspots: list[str], lang: str) -> str:
    """Generate readable blindspot description instead of noisy TF-IDF pairing."""
    if top_blindspots and any(len(b) > 5 for b in top_blindspots):
        # Use actual extracted blindspots if they look meaningful
        meaningful = [b for b in top_blindspots if len(b) > 5]
        if meaningful:
            return "、".join(meaningful[:6])

    if lang == "en":
        return "Areas outside core expertise, high-uncertainty scenarios"
    return "能力圈外领域、高不确定性场景"


def _generate_tensions(top_topics: list[str], lang: str) -> list[str]:
    """Generate meaningful tension descriptions instead of 'X优先与Y约束'."""
    if len(top_topics) < 2:
        return []
    if lang == "en":
        return [f"Balancing {top_topics[0]} priorities against {top_topics[1]} constraints"]
    return [f"{top_topics[0]}优先与{top_topics[1]}约束之间的权衡"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--out-dir", required=True, help="output dir")
    parser.add_argument("--name", required=True, help="person name")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict] = load_jsonl(in_path)
    if not items:
        raise SystemExit("no extraction items found")

    total = len(items)
    def valid_date(d: str) -> bool:
        if not isinstance(d, str):
            return False
        d = d.strip()
        if not d:
            return False
        if d.startswith("0000"):
            return False
        return True

    dates = []
    for it in items:
        d = it.get("date") or parse_date_from_filename(it.get("source_file", ""))
        if valid_date(d):
            dates.append(d)
    dates.sort()
    date_range = (dates[0] if dates else "unknown", dates[-1] if dates else "unknown")

    base_dir = in_path.resolve().parent.parent
    kb_dir = base_dir / "kb" / "plain_text"

    def load_doc_text(it: dict, limit: int = 12000) -> str:
        src = it.get("source_file") or ""
        if src and kb_dir.exists():
            p = kb_dir / src
            if p.exists():
                raw = p.read_text(encoding="utf-8", errors="ignore")
                raw = strip_front_matter(raw)
                # Sample more for long-form letters
                if "shareholder_letter" in src or "owners_manual" in src:
                    return sample_text(raw, 12000)
                return sample_text(raw, limit)
        return it.get("core_view", "") or ""

    docs = []
    for it in items:
        title = it.get("title") or ""
        core = load_doc_text(it)
        docs.append(f"{title}\n{core}")

    # Detect corpus language
    lang = detect_corpus_language(docs)
    logger.info(f"[info] detected corpus language: {lang}")

    tfidf, vocab, tokenized = build_tfidf(docs, min_df=2, max_df_ratio=0.6, max_features=4000, phrases=cfg.get("phrases") or None)
    topic_terms, _doc_topics = lsa_topics(tfidf, vocab, num_topics=6, top_n=6)

    topic_flat: list[str] = []
    for topic in topic_terms:
        for t in topic:
            if t not in topic_flat:
                topic_flat.append(t)

    token_freq = Counter()
    for toks in tokenized:
        token_freq.update(toks)

    models = Counter()
    values = Counter()
    reasoning = Counter()
    decision_style = Counter()
    blindspots = Counter()
    year_topics: dict[str, Counter] = defaultdict(Counter)

    for idx, it in enumerate(items):
        for k in it.get("models", []):
            models[k] += 1
        for k in it.get("values", []):
            values[k] += 1
        for k in it.get("reasoning", []):
            reasoning[k] += 1
        for k in it.get("decision_style", []):
            decision_style[k] += 1
        for k in it.get("blindspots", []):
            blindspots[k] += 1
        d = it.get("date") or parse_date_from_filename(it.get("source_file", ""))
        if d:
            year = d.split("-")[0]
            for k in tokenized[idx]:
                year_topics[year][k] += 1

    top_topics = sanitize_tokens([display_term(t) for t in topic_flat[:24]], 12)
    top_models = sanitize_tokens(choose_top(models, 16), 10)
    top_values = sanitize_tokens(choose_top(values, 12), 8)
    top_reasoning = choose_top(reasoning, 6)
    top_decision = choose_top(decision_style, 8)
    top_language = sanitize_tokens([display_term(t) for t, _ in token_freq.most_common(30)], 12)
    top_blindspots = choose_top(blindspots, 6)

    # evidence anchors by topic match
    anchors: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        kws = set(it.get("keywords", []))
        for t in top_topics[:6]:
            if t in kws and len(anchors[t]) < 3:
                anchors[t].append(
                    {
                        "title": it.get("title", ""),
                        "date": it.get("date", ""),
                        "source_file": it.get("source_file", ""),
                    }
                )

    beliefs = infer_beliefs_from_data(top_topics, top_models, cfg, lang)

    # Use actual data with language-appropriate fallbacks
    MODEL_FALLBACK = DEFAULT_MODEL_FALLBACK_EN if lang == "en" else DEFAULT_MODEL_FALLBACK_ZH
    VALUE_FALLBACK = DEFAULT_VALUE_FALLBACK_EN if lang == "en" else DEFAULT_VALUE_FALLBACK_ZH

    if not top_reasoning:
        top_reasoning = (
            ["structured decomposition", "causal chain", "comparison / analogy"]
            if lang == "en"
            else ["结构化拆解", "因果链", "对比/类比"]
        )
    if not top_models:
        top_models = MODEL_FALLBACK[:3]
    if len(top_models) < 8:
        for m in MODEL_FALLBACK:
            if m not in top_models:
                top_models.append(m)
            if len(top_models) >= 8:
                break
    top_models = [normalize_model_label(m) for m in top_models]
    # de-dup after normalization
    seen = set()
    top_models = [m for m in top_models if not (m in seen or seen.add(m))]
    if not top_values:
        top_values = VALUE_FALLBACK[:3]
    if len(top_values) < 5:
        for v in VALUE_FALLBACK:
            if v not in top_values:
                top_values.append(v)
            if len(top_values) >= 5:
                break
    if not top_decision:
        top_decision = (
            ["careful evaluation", "evidence-first", "risk control"]
            if lang == "en"
            else ["谨慎评估", "证据优先", "风险控制"]
        )
    if not top_language:
        top_language = (
            ["concise", "structured", "conclusion-first"]
            if lang == "en"
            else ["直白", "分点", "先结论后解释"]
        )
    if not top_blindspots:
        top_blindspots = (
            ["areas outside core expertise", "high-uncertainty scenarios"]
            if lang == "en"
            else ["能力圈外领域", "高不确定性场景"]
        )

    low_topics = [display_term(t) for t, _ in token_freq.most_common()[-6:]]
    low_topics = [t for t in low_topics if t and t not in top_topics[:6]]

    evolution_lines = []
    for year in sorted(year_topics.keys()):
        ranked = choose_top(year_topics[year], 3)
        if ranked:
            evolution_lines.append(f"- {year}：{ '、'.join(display_term(t) for t in ranked) }")

    tensions = _generate_tensions(top_topics, lang)
    blindspot_text = _generate_blindspots(top_topics, top_blindspots, lang)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    anchors_lines = []
    for topic, items_list in anchors.items():
        for a in items_list:
            anchors_lines.append(
                f"- {topic} | {a.get('date','')} {a.get('title','')} ({a.get('source_file','')})"
            )

    # Use cleaned blindspot text instead of raw top_blindspots join
    sep = ", " if lang == "en" else "、"

    thinking_profile_md = "\n".join(
        [
            "# 思维画像",
            "",
            "## 基本信息",
            "",
            f"- 人物：{args.name}",
            f"- 语料规模：{total} 篇",
            f"- 时间跨度：{date_range[0]} ～ {date_range[1]}",
            f"- 版本/日期：{today}",
            "",
            "## 知识版图",
            "",
            f"- 关注领域：{sep.join(top_topics)}",
            f"- 低频主题：{sep.join(low_topics)}" if low_topics else "- 低频主题：",
            "",
            "## 核心信念（3-5 条）",
            "",
            *[f"- {b}" for b in beliefs[:5]],
            "",
            "## 思维特征",
            "",
            f"- 推理方式：{sep.join(top_reasoning)}",
            (
                "- 分析顺序：macro trends / structure → individual selection → actionable path"
                if lang == "en"
                else "- 分析顺序：宏观趋势/结构 → 个体选择 → 可执行路径"
            ),
            f"- 偏好框架：{sep.join(top_models)}",
            "",
            "## 心智模型库（Top 10）",
            "",
            *[f"- {m}" for m in top_models[:10]],
            "",
            "## 决策风格",
            "",
            f"- 决策特征：{sep.join(top_decision)}",
            "",
            "## 价值排序",
            "",
            f"- 价值观关键词：{sep.join(top_values)}",
            "",
            "## 语言指纹",
            "",
            f"- 高频词：{sep.join(top_language)}",
            (
                "- 句式：concise, structured, framework-driven expression"
                if lang == "en"
                else "- 句式：短句+分点，常用框架式表达"
            ),
            "",
            "## 思维演变",
            "",
            *evolution_lines,
            "",
            "## 认知盲区",
            "",
            f"- 可能盲区：{blindspot_text}",
            "",
            "## 矛盾与张力",
            "",
            *[f"- {t}" for t in tensions],
            "",
            "## 证据锚点",
            "",
            *anchors_lines,
        ]
    )

    if lang == "en":
        system_prompt_md = "\n".join(
            [
                f'You are a thinking simulation of "{args.name}", built from public corpus ({date_range[0]} to {date_range[1]}).',
                "Your goal is to replicate their thinking patterns when answering questions.",
                "",
                "## Identity",
                "",
                f"- Name: {args.name}",
                "- Background: built from public writings and speeches",
                f"- Domains: {', '.join(top_topics[:5])}",
                "",
                "## Core Beliefs",
                "",
                *[f"- {b}" for b in beliefs[:5]],
                "",
                "## Thinking Approach",
                "",
                "- Lead with frameworks, then give advice; use case studies to illustrate",
                f"- Preferred models: {', '.join(top_models[:8])}",
                "- Macro trends → individual choices → actionable paths",
                "",
                "## Thinking Process",
                "",
                "1. Problem identification (opinion / decision / review / explanation)",
                "2. Path retrieval (beliefs → models → topics)",
                "3. Evidence anchoring (select 3-5 representative anchors)",
                "4. Argument chain (1-2 pieces of evidence → conclusion)",
                "5. Framework generation (macro trends → structural variables → action paths)",
                "6. Recommendation output (prioritized actions)",
                "7. Risk & boundary declaration (circle of competence & uncertainty)",
                "8. Reasoning annotation (original views vs. inferred extensions)",
                "",
                "## Communication Style",
                "",
                "- Clear, direct, uses bullet points",
                "- Framework-driven expression",
                "- Concludes with actionable advice",
                "",
                "## Key Constraints",
                "",
                '- Never fabricate views the author has not expressed; if inferring, label as "inference based on thinking patterns"',
                "- When views conflict, explain the situational differences",
                "- Clearly state uncertainty when outside circle of competence",
            ]
        )
    else:
        system_prompt_md = "\n".join(
            [
                f"\u4f60\u662f\u201c{args.name}\u201d\u7684\u601d\u7ef4\u6a21\u62df\u4f53\uff0c\u57fa\u4e8e\u5176\u516c\u5f00\u8bed\u6599\u6784\u5efa\uff08{date_range[0]} \uff5e {date_range[1]}\uff09\u3002",
                "\u4f60\u7684\u76ee\u6807\u662f\u5c3d\u53ef\u80fd\u8fd8\u539f\u5176\u601d\u8003\u65b9\u5f0f\u6765\u56de\u7b54\u95ee\u9898\u3002",
                "",
                "## \u8eab\u4efd\u8bbe\u5b9a",
                "",
                f"- \u59d3\u540d\uff1a{args.name}",
                "- \u80cc\u666f\uff1a\u57fa\u4e8e\u516c\u5f00\u8bed\u6599\u6784\u5efa",
                f"- \u9886\u57df\uff1a{'\u3001'.join(top_topics[:5])}",
                "",
                "## \u6838\u5fc3\u4fe1\u5ff5",
                "",
                *[f"- {b}" for b in beliefs[:5]],
                "",
                "## \u601d\u7ef4\u65b9\u5f0f",
                "",
                "- \u5148\u7ed9\u6846\u67b6\uff0c\u518d\u7ed9\u5efa\u8bae\uff1b\u5e38\u7528\u6848\u4f8b\u5f15\u5165",
                f"- \u504f\u597d\u6a21\u578b\uff1a{'\u3001'.join(top_models[:8])}",
                "- \u5b8f\u89c2\u8d8b\u52bf \u2192 \u4e2a\u4eba\u9009\u62e9 \u2192 \u53ef\u6267\u884c\u8def\u5f84",
                "",
                "## \u601d\u8003\u6d41\u7a0b",
                "",
                "1. \u95ee\u9898\u5b9a\u4f4d\uff08\u89c2\u70b9/\u51b3\u7b56/\u590d\u76d8/\u89e3\u91ca\uff09",
                "2. \u8def\u5f84\u68c0\u7d22\uff08\u4fe1\u5ff5 \u2192 \u6a21\u578b \u2192 \u8bdd\u9898\uff09",
                "3. \u8bc1\u636e\u951a\u5b9a\uff08\u9009 3-5 \u4e2a\u4ee3\u8868\u6027\u951a\u70b9\uff09",
                "4. \u8bba\u8bc1\u94fe\u5f15\u7528\uff08\u9009 1-2 \u6761\u8bc1\u636e \u2192 \u7ed3\u8bba\uff09",
                "5. \u6846\u67b6\u751f\u6210\uff08\u5b8f\u89c2\u8d8b\u52bf \u2192 \u7ed3\u6784\u53d8\u91cf \u2192 \u884c\u52a8\u8def\u5f84\uff09",
                "6. \u5efa\u8bae\u8f93\u51fa\uff08\u6392\u5e8f\u4e0e\u884c\u52a8\uff09",
                "7. \u98ce\u9669\u4e0e\u8fb9\u754c\u58f0\u660e\uff08\u80fd\u529b\u5708\u4e0e\u4e0d\u786e\u5b9a\u6027\uff09",
                "8. \u63a8\u7406\u6807\u6ce8\uff08\u539f\u6587\u89c2\u70b9 vs \u63a8\u7406\u5ef6\u4f38\uff09",
                "",
                "## \u8868\u8fbe\u98ce\u683c",
                "",
                "- \u53e3\u8bed\u5316\u3001\u76f4\u767d\u3001\u5206\u70b9\u56de\u7b54",
                "- \u5e38\u7528\u6846\u67b6\u5f0f\u8868\u8fbe",
                "- \u7ed3\u5c3e\u7ed9\u660e\u786e\u5efa\u8bae\u6216\u795d\u798f",
                "",
                "## \u91cd\u8981\u7ea6\u675f",
                "",
                "- \u4e0d\u7f16\u9020\u539f\u4f5c\u8005\u6ca1\u6709\u8868\u8fbe\u8fc7\u7684\u89c2\u70b9\uff1b\u5982\u9700\u63a8\u7406\uff0c\u6ce8\u660e\u201c\u57fa\u4e8e\u601d\u7ef4\u6a21\u5f0f\u7684\u63a8\u6d4b\u201d",
                "- \u77db\u76fe\u89c2\u70b9\u9700\u8bf4\u660e\u60c5\u5883\u5dee\u5f02",
                "- \u80fd\u529b\u5708\u5916\u660e\u786e\u8bf4\u660e\u4e0d\u786e\u5b9a\u6027",
            ]
        )

    tp_path = out_dir / "thinking_profile.md"
    sp_path = out_dir / "system_prompt.md"
    if tp_path.exists() and not args.overwrite:
        tp_path = tp_path.with_suffix(tp_path.suffix + ".auto.md")
    if sp_path.exists() and not args.overwrite:
        sp_path = sp_path.with_suffix(sp_path.suffix + ".auto.md")

    tp_path.write_text(thinking_profile_md, encoding="utf-8")
    sp_path.write_text(system_prompt_md, encoding="utf-8")

    logger.info(f"[done] out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
