#!/usr/bin/env python3
"""Build a typed relation graph from plain_text and extractions."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from utils import load_jsonl, split_sentences, setup_logging
from domain_config import load_config

logger = setup_logging(__name__)

REL_PATTERNS = {
    "causal": ["因为", "所以", "因此", "导致", "结果", "本质",
               "because", "therefore", "thus", "hence", "leads to", "results in", "causes"],
    "contrast": ["不是", "而是", "相反", "对比", "相比", "不同", "反过来", "但是", "但", "不过",
                 "however", "in contrast", "on the other hand", "unlike", "whereas", "nevertheless"],
    "analogy": ["像", "比如", "例如", "类似", "好比",
                "for example", "for instance", "similar to", "analogous", "just as"],
    "advice": ["建议", "应该", "不要", "尽量", "优先", "最好", "必须", "需要", "可以", "别",
               "should", "must", "recommend", "avoid", "prefer", "better to", "ought to"],
}



def detect_rel_types(sentence: str) -> set[str]:
    types = set()
    for rel, pats in REL_PATTERNS.items():
        if any(p in sentence for p in pats):
            types.add(rel)
    return types


def top_keywords(items: list[dict], top_n: int) -> list[str]:
    c = Counter()
    for it in items:
        for k in it.get("keywords", []) or []:
            c[k] += 1
    return [k for k, _ in c.most_common(top_n)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractions", required=True, help="extractions.jsonl")
    parser.add_argument("--plain-text-dir", required=True, help="plain_text folder")
    parser.add_argument("--out-dir", required=True, help="output dir")
    parser.add_argument("--top-keywords", type=int, default=40)
    parser.add_argument("--min-edge", type=int, default=3)
    parser.add_argument("--max-edges", type=int, default=200)
    parser.add_argument("--config", default=None, help="domain_config.json path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    generic_terms = set(cfg.get("generic_terms", []))

    items = load_jsonl(Path(args.extractions))
    if not items:
        raise SystemExit("no items")

    kw_list = top_keywords(items, args.top_keywords)
    kw_list = [k for k in kw_list if k not in generic_terms]
    kw_set = set(kw_list)

    plain_dir = Path(args.plain_text_dir)
    edges = Counter()
    node_weight = Counter()

    for it in items:
        source_file = it.get("source_file", "")
        if not source_file:
            continue
        path = plain_dir / source_file
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        sentences = split_sentences(text)
        for s in sentences:
            rel_types = detect_rel_types(s)
            if not rel_types:
                continue
            present = [k for k in kw_set if k in s]
            if len(present) < 2:
                continue
            for k in present:
                node_weight[k] += 1
            for a, b in combinations(sorted(set(present)), 2):
                for rel in rel_types:
                    key = (a, b, rel)
                    edges[key] += 1

    # Build graph
    nodes = [
        {
            "id": k,
            "label": k,
            "type": "keyword",
            "weight": node_weight.get(k, 1),
        }
        for k in kw_list
    ]

    edge_list = [
        {"source": a, "target": b, "type": rel, "weight": w}
        for (a, b, rel), w in edges.items()
        if w >= args.min_edge
    ]
    edge_list.sort(key=lambda x: x["weight"], reverse=True)
    edge_list = edge_list[: args.max_edges]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    graph = {"nodes": nodes, "edges": edge_list}
    (out_dir / "relation_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Mermaid
    mermaid = ["graph LR"]
    id_map = {k: f"n{idx}" for idx, k in enumerate(kw_list)}
    for k in kw_list:
        mermaid.append(f"  {id_map[k]}[\"{k}\"]")
    for e in edge_list:
        mermaid.append(
            f"  {id_map[e['source']]} -- {e['type']}:{e['weight']} --> {id_map[e['target']]}"
        )
    (out_dir / "relation_graph.mmd").write_text("\n".join(mermaid), encoding="utf-8")

    # Report
    rel_groups = defaultdict(list)
    for e in edge_list:
        rel_groups[e["type"]].append(e)

    report = ["# 关系图谱摘要", ""]
    report.append(f"- 节点数：{len(nodes)}")
    report.append(f"- 边数：{len(edge_list)}")
    report.append("")
    for rel, edges_r in rel_groups.items():
        report.append(f"## {rel} 关系")
        report.append("")
        for e in edges_r[:15]:
            report.append(f"- {e['source']} ↔ {e['target']} ({e['weight']})")
        report.append("")

    (out_dir / "relation_report.md").write_text("\n".join(report), encoding="utf-8")

    logger.info(f"[done] out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
