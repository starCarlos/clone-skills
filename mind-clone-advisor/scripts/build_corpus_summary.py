#!/usr/bin/env python3
"""Summarize extractions.jsonl into analysis/corpus_summary.json + .md."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from utils import load_jsonl, setup_logging

logger = setup_logging(__name__)


def choose_top(counter: Counter, n: int) -> list[str]:
    return [k for k, _ in counter.most_common(n)]


def _valid_date(d: str) -> bool:
    if not isinstance(d, str):
        return False
    d = d.strip()
    if not d:
        return False
    if d.startswith("0000"):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    in_path = Path(args.input)
    items = load_jsonl(in_path)
    if not items:
        raise SystemExit("no items")

    dates = [it.get("date", "") for it in items if _valid_date(it.get("date", ""))]
    dates = [d for d in dates if isinstance(d, str) and d]
    dates.sort()
    date_range = {"start": dates[0] if dates else "unknown", "end": dates[-1] if dates else "unknown"}

    keywords = Counter()
    models = Counter()
    values = Counter()
    reasoning = Counter()
    decision_style = Counter()
    language = Counter()
    blindspots = Counter()
    stances = Counter()

    for it in items:
        for k in it.get("keywords", []) or []:
            keywords[k] += 1
        for k in it.get("models", []) or []:
            models[k] += 1
        for k in it.get("values", []) or []:
            values[k] += 1
        for k in it.get("reasoning", []) or []:
            reasoning[k] += 1
        for k in it.get("decision_style", []) or []:
            decision_style[k] += 1
        for k in it.get("language_fingerprint", []) or []:
            language[k] += 1
        for k in it.get("blindspots", []) or []:
            blindspots[k] += 1
        for k in it.get("stances", []) or []:
            stances[k] += 1

    summary = {
        "total": len(items),
        "date_range": date_range,
        "top_keywords": choose_top(keywords, 20),
        "top_models": choose_top(models, 12),
        "top_values": choose_top(values, 10),
        "top_reasoning": choose_top(reasoning, 8),
        "top_decision_style": choose_top(decision_style, 8),
        "top_language_markers": choose_top(language, 12),
        "top_blindspots": choose_top(blindspots, 6),
        "top_stances": choose_top(stances, 8),
        "field_coverage": {
            "keywords": sum(1 for it in items if it.get("keywords")),
            "models": sum(1 for it in items if it.get("models")),
            "values": sum(1 for it in items if it.get("values")),
            "reasoning": sum(1 for it in items if it.get("reasoning")),
            "decision_style": sum(1 for it in items if it.get("decision_style")),
            "language_fingerprint": sum(1 for it in items if it.get("language_fingerprint")),
            "blindspots": sum(1 for it in items if it.get("blindspots")),
            "stances": sum(1 for it in items if it.get("stances")),
            "evidence_anchors": sum(1 for it in items if it.get("evidence_anchors")),
        },
    }

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    if out_json.exists() and not args.overwrite:
        out_json = out_json.with_suffix(out_json.suffix + ".auto.json")
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# 语料摘要")
    lines.append("")
    lines.append(f"- 总篇数：{summary['total']}")
    lines.append(f"- 时间跨度：{summary['date_range']['start']} ～ {summary['date_range']['end']}")
    lines.append("")
    lines.append("## 高频关键词")
    lines.append("")
    lines.append("、".join(summary["top_keywords"]) or "（空）")
    lines.append("")
    lines.append("## 高频模型/框架")
    lines.append("")
    lines.append("、".join(summary["top_models"]) or "（空）")
    lines.append("")
    lines.append("## 价值观关键词")
    lines.append("")
    lines.append("、".join(summary["top_values"]) or "（空）")
    lines.append("")
    lines.append("## 推理方式")
    lines.append("")
    lines.append("、".join(summary["top_reasoning"]) or "（空）")
    lines.append("")
    lines.append("## 决策风格")
    lines.append("")
    lines.append("、".join(summary["top_decision_style"]) or "（空）")
    lines.append("")
    lines.append("## 语言指纹")
    lines.append("")
    lines.append("、".join(summary["top_language_markers"]) or "（空）")
    lines.append("")
    lines.append("## 维度覆盖统计")
    lines.append("")
    for k, v in summary["field_coverage"].items():
        lines.append(f"- {k}: {v}/{summary['total']}")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    if out_md.exists() and not args.overwrite:
        out_md = out_md.with_suffix(out_md.suffix + ".auto.md")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    logger.info(f"[done] out={out_json} {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
