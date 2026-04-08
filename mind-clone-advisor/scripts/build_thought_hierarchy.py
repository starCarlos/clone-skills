#!/usr/bin/env python3
"""Build a concept hierarchy: beliefs -> models -> topics."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from domain_config import load_config
from utils import load_jsonl, setup_logging

logger = setup_logging(__name__)


def top(counter: Counter, n: int, exclude: set[str] | None = None) -> list[str]:
    if exclude is None:
        exclude = set()
    return [k for k, _ in counter.most_common(n) if k not in exclude]


def pick_representatives(items: list[dict], key: str, value: str, n: int = 3) -> list[dict]:
    out = []
    for it in items:
        if value in (it.get(key, []) or []):
            out.append(
                {
                    "title": it.get("title", ""),
                    "date": it.get("date", ""),
                    "source_file": it.get("source_file", ""),
                }
            )
        if len(out) >= n:
            break
    return out


def pick_by_any_keyword(items: list[dict], keywords: set[str], n: int = 3) -> list[dict]:
    out = []
    for it in items:
        kw = set(it.get("keywords", []) or [])
        if kw & keywords:
            out.append(
                {
                    "title": it.get("title", ""),
                    "date": it.get("date", ""),
                    "source_file": it.get("source_file", ""),
                }
            )
        if len(out) >= n:
            break
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--out-dir", required=True, help="output dir")
    parser.add_argument("--top-models", type=int, default=12)
    parser.add_argument("--top-topics", type=int, default=10)
    parser.add_argument("--config", default=None, help="domain_config.json path")
    args = parser.parse_args()

    items = load_jsonl(Path(args.input))
    if not items:
        raise SystemExit("no items")

    cfg = load_config(args.config)
    belief_buckets = cfg.get("belief_buckets", {}) or {}
    theme_seeds = cfg.get("theme_seeds", {}) or {}
    generic_terms = set(cfg.get("generic_terms", []))

    model_counter = Counter()
    keyword_counter = Counter()

    for it in items:
        for m in it.get("models", []) or []:
            model_counter[m] += 1
        for k in it.get("keywords", []) or []:
            keyword_counter[k] += 1

    models = top(model_counter, args.top_models)
    topics = top(keyword_counter, args.top_topics, exclude=generic_terms)

    # model -> topic co-occur
    model_topics = {m: Counter() for m in models}
    for it in items:
        it_models = set(it.get("models", []) or [])
        it_topics = set(it.get("keywords", []) or [])
        for m in it_models:
            if m in model_topics:
                for t in it_topics:
                    model_topics[m][t] += 1

    model_to_topics = {}
    for m in models:
        top_t = [
            t for t, _ in model_topics[m].most_common(8) if t not in generic_terms
        ]
        model_to_topics[m] = top_t[:6]

    # belief -> models mapping
    if not belief_buckets:
        if theme_seeds:
            belief_buckets = {f"主题:{k}": set(v) for k, v in theme_seeds.items()}
        else:
            belief_buckets = {"核心主题": set(topics[:6])}

    belief_map = {b: [] for b in belief_buckets}
    for m in models:
        assigned = False
        for belief, kws in belief_buckets.items():
            if m in kws or any(k in m for k in kws):
                belief_map[belief].append(m)
                assigned = True
                break
        if not assigned:
            belief_map.setdefault("其他框架", []).append(m)

    # Fill buckets with matching keywords if empty
    for belief, kws in belief_buckets.items():
        if belief_map.get(belief):
            continue
        for k in kws:
            if keyword_counter.get(k, 0) > 0:
                belief_map[belief].append(k)

    # Representatives
    model_reps = {m: pick_representatives(items, "models", m, n=3) for m in models}
    topic_reps = {t: pick_representatives(items, "keywords", t, n=3) for t in topics}
    belief_reps = {
        belief: pick_by_any_keyword(items, set(kws), n=3)
        for belief, kws in belief_buckets.items()
    }

    hierarchy = {
        "beliefs": [
            {
                "belief": b,
                "models": [
                    {
                        "model": m,
                        "topics": model_to_topics.get(m, []),
                        "representatives": model_reps.get(m, []),
                    }
                    for m in ms
                ],
                "representatives": belief_reps.get(b, []),
            }
            for b, ms in belief_map.items()
        ],
        "top_models": models,
        "top_topics": topics,
        "topic_representatives": topic_reps,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "thought_hierarchy.json").write_text(
        json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown
    lines = ["# 思维层级图谱", ""]
    for b in hierarchy["beliefs"]:
        lines.append(f"## {b['belief']}")
        lines.append("")
        if b.get("representatives"):
            lines.append("- 代表文章：")
            for r in b["representatives"]:
                lines.append(f"  - {r['date']} {r['title']} ({r['source_file']})")
            lines.append("")
        if not b["models"]:
            lines.append("- （暂无）")
            lines.append("")
            continue
        for m in b["models"]:
            lines.append(f"- {m['model']}")
            if m["topics"]:
                lines.append(f"  关联话题：{'、'.join(m['topics'])}")
            reps = m.get("representatives") or []
            if reps:
                lines.append("  代表文章：")
                for r in reps:
                    lines.append(f"    - {r['date']} {r['title']} ({r['source_file']})")
        lines.append("")

    (out_dir / "thought_hierarchy.md").write_text("\n".join(lines), encoding="utf-8")

    logger.info(f"[done] out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
