#!/usr/bin/env python3
"""Build a thought graph from extraction JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from utils import load_jsonl, setup_logging
from domain_config import load_config

logger = setup_logging(__name__)


def top_n(counter: Counter, n: int) -> set[str]:
    return set([k for k, _ in counter.most_common(n)])


def sanitize(s: str) -> str:
    return s.replace("\n", " ").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--out-dir", required=True, help="output dir")
    parser.add_argument("--top-keywords", type=int, default=40)
    parser.add_argument("--top-models", type=int, default=20)
    parser.add_argument("--top-values", type=int, default=12)
    parser.add_argument("--top-styles", type=int, default=12)
    parser.add_argument("--min-edge", type=int, default=3)
    parser.add_argument("--max-edges", type=int, default=160)
    parser.add_argument("--config", default=None, help="domain_config.json path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    generic_terms = set(cfg.get("generic_terms", []))

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    items = load_jsonl(in_path)
    if not items:
        raise SystemExit("no items")

    kw = Counter()
    models = Counter()
    values = Counter()
    styles = Counter()

    for it in items:
        for k in it.get("keywords", []) or []:
            kw[k] += 1
        for k in it.get("models", []) or []:
            models[k] += 1
        for k in it.get("values", []) or []:
            values[k] += 1
        for k in it.get("decision_style", []) or []:
            styles[k] += 1

    kw_set = top_n(kw, args.top_keywords) - generic_terms
    model_set = top_n(models, args.top_models) - generic_terms
    value_set = top_n(values, args.top_values) - generic_terms
    style_set = top_n(styles, args.top_styles) - generic_terms

    node_types = {}
    node_weight = {}
    for k in kw_set:
        node_types[k] = "keyword"
        node_weight[k] = kw[k]
    for k in model_set:
        node_types[k] = "model"
        node_weight[k] = models[k]
    for k in value_set:
        node_types[k] = "value"
        node_weight[k] = values[k]
    for k in style_set:
        node_types[k] = "style"
        node_weight[k] = styles[k]

    edges = Counter()
    for it in items:
        nodes = set()
        for k in it.get("keywords", []) or []:
            if k in kw_set:
                nodes.add(k)
        for k in it.get("models", []) or []:
            if k in model_set:
                nodes.add(k)
        for k in it.get("values", []) or []:
            if k in value_set:
                nodes.add(k)
        for k in it.get("decision_style", []) or []:
            if k in style_set:
                nodes.add(k)
        nodes = sorted(nodes)
        for a, b in combinations(nodes, 2):
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            edges[key] += 1

    # Build edge list
    edge_list = [
        {
            "source": a,
            "target": b,
            "weight": w,
        }
        for (a, b), w in edges.items()
        if w >= args.min_edge
    ]
    edge_list.sort(key=lambda x: x["weight"], reverse=True)
    edge_list = edge_list[: args.max_edges]

    nodes = [
        {
            "id": k,
            "label": k,
            "type": node_types[k],
            "weight": node_weight[k],
        }
        for k in node_types.keys()
    ]

    graph = {
        "nodes": nodes,
        "edges": edge_list,
        "meta": {
            "total_items": len(items),
            "top_keywords": args.top_keywords,
            "top_models": args.top_models,
            "top_values": args.top_values,
            "top_styles": args.top_styles,
            "min_edge": args.min_edge,
        },
    }

    (out_dir / "thought_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Mermaid
    mermaid_lines = ["graph LR"]
    for n in nodes:
        label = sanitize(n["label"])
        mermaid_lines.append(f"  {hash(label)}[\"{label}\"]")
    for e in edge_list:
        a = hash(e["source"])
        b = hash(e["target"])
        mermaid_lines.append(f"  {a} -- {e['weight']} --> {b}")

    (out_dir / "thought_graph.mmd").write_text("\n".join(mermaid_lines), encoding="utf-8")

    # Report
    degree = Counter()
    for e in edge_list:
        degree[e["source"]] += e["weight"]
        degree[e["target"]] += e["weight"]

    report = []
    report.append("# 思维图谱摘要")
    report.append("")
    report.append(f"- 节点数：{len(nodes)}")
    report.append(f"- 边数：{len(edge_list)}")
    report.append("")
    report.append("## Top 枢纽节点")
    report.append("")
    for k, w in degree.most_common(15):
        report.append(f"- {k}: {w}")
    report.append("")
    report.append("## Top 关系边")
    report.append("")
    for e in edge_list[:20]:
        report.append(f"- {e['source']} ↔ {e['target']} (共现 {e['weight']})")

    (out_dir / "graph_report.md").write_text("\n".join(report), encoding="utf-8")

    logger.info(f"[done] out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
