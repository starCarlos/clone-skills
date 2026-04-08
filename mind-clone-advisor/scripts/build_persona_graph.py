#!/usr/bin/env python3
"""Build persona graphs from plain_text only (deterministic).

Uses domain_config.json for domain-specific terms. Generic language patterns
(REL_PATTERNS, CAUSE_PATTERNS, EVIDENCE_MARKERS) are preserved as they're
language-level features, not domain-specific.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from domain_config import (
    CAUSE_PATTERNS_RAW,
    EVIDENCE_MARKERS,
    MODEL_SUFFIXES,
    REL_PATTERNS,
    STOPWORDS_CJK,
    STOPWORDS_EN,
    STYLE_WORDS,
    VALUE_SUFFIXES,
    load_config,
)
from utils import extract_title, parse_date_from_filename, split_paragraphs, setup_logging

logger = setup_logging(__name__)


def compile_cause_patterns():
    """Compile regex patterns from raw tuples."""
    return [(re.compile(pat), rel) for pat, rel in CAUSE_PATTERNS_RAW]


CAUSE_PATTERNS = compile_cause_patterns()

"""
Domain-specific terms (theme seeds, model/value/style terms, generic terms, etc.)
must be loaded from domain_config.json. This script intentionally avoids
hardcoded domain assumptions.
"""

# CJK and EN regex patterns
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


# -------------------------
# Helpers
# -------------------------


def clean_text(text: str, cleanup_patterns: list[str]) -> str:
    """Clean text using domain-specific cleanup patterns from config."""
    text = text.replace("\u200d", "")
    for pat in cleanup_patterns:
        text = text.replace(pat, "")
    return text


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?\n]+", text)
    result = []
    for p in parts:
        sub = re.split(r"\.\s+(?=[A-Z])", p)
        result.extend(sub)
    return [p.strip() for p in result if p.strip()]




def detect_rel_types(sentence: str) -> set[str]:
    types = set()
    for rel, pats in REL_PATTERNS.items():
        if any(p in sentence for p in pats):
            types.add(rel)
    return types


def is_noise_token(tok: str) -> bool:
    if tok in STOPWORDS_CJK:
        return True
    if len(tok) < 2:
        return True
    if any(ch.isdigit() for ch in tok):
        return True
    if len(set(tok)) == 1:
        return True
    return False


def iter_cjk_ngrams(text: str, min_n: int = 2, max_n: int = 4) -> set[str]:
    out = set()
    for seq in CJK_RE.findall(text):
        if len(seq) < min_n:
            continue
        max_len = min(max_n, len(seq))
        for n in range(min_n, max_len + 1):
            for i in range(len(seq) - n + 1):
                token = seq[i : i + n]
                if is_noise_token(token):
                    continue
                out.add(token)
    return out


def extract_doc_tokens(text: str, seed_keywords: list[str]) -> set[str]:
    """Extract tokens from text using seed keywords from config."""
    tokens = set()
    tokens |= iter_cjk_ngrams(text)
    for word in EN_RE.findall(text):
        w = word.lower()
        if w in STOPWORDS_EN:
            continue
        tokens.add(w)
    for kw in seed_keywords:
        if kw and kw in text:
            tokens.add(kw)
    return tokens


def top_by_counter(counter: Counter, n: int) -> list[str]:
    items = sorted(counter.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
    return [k for k, _ in items[:n]]


def sanitize_label(s: str) -> str:
    return s.replace("\n", " ").replace('"', "'").strip()


def normalize(counter: Counter) -> dict[str, float]:
    if not counter:
        return {}
    max_v = max(counter.values())
    return {k: round(v / max_v, 3) for k, v in counter.items()}


# -------------------------
# Core Builders
# -------------------------


def build_extractions(
    items: list[dict],
    top_keywords: int,
    max_keywords_per_doc: int,
    seed_keywords: list[str],
    model_terms: list[str],
    value_terms: list[str],
    style_terms: list[str],
    min_df: int | None = None,
) -> tuple[list[dict], list[str], Counter]:
    """Build extractions using domain-specific terms from config."""
    df = Counter()
    doc_tokens = []
    for it in items:
        tokens = extract_doc_tokens(it["text"], seed_keywords)
        doc_tokens.append(tokens)
        for tok in tokens:
            df[tok] += 1

    if min_df is None:
        min_df = 2 if len(items) >= 20 else 1

    candidates = [k for k, v in df.items() if v >= min_df]
    candidates.sort(key=lambda k: (-df[k], -len(k), k))
    top_list = candidates[:top_keywords]

    # Force include seed keywords if present
    for kw in seed_keywords:
        if df.get(kw, 0) >= min_df and kw not in top_list:
            top_list.append(kw)

    top_list = sorted(set(top_list), key=lambda k: (-df[k], -len(k), k))

    model_set = set(model_terms)
    value_set = set(value_terms)
    style_set = set(style_terms)

    enriched = []
    for it, tokens in zip(items, doc_tokens):
        text = it["text"]
        keywords_all = [k for k in top_list if k in text]
        if max_keywords_per_doc > 0:
            keywords = keywords_all[:max_keywords_per_doc]
        else:
            keywords = keywords_all

        models = []
        values = []
        styles = []
        for k in keywords_all:
            if k in model_set or k.endswith(MODEL_SUFFIXES):
                models.append(k)
            if k in value_set or k.endswith(VALUE_SUFFIXES):
                values.append(k)
            if k in style_set:
                styles.append(k)

        enriched.append(
            {
                "title": it["title"],
                "date": it["date"],
                "source_file": it["source_file"],
                "keywords": keywords,
                "models": sorted(set(models), key=lambda x: (-len(x), x)),
                "values": sorted(set(values), key=lambda x: (-len(x), x)),
                "decision_style": sorted(set(styles), key=lambda x: (-len(x), x)),
            }
        )

    return enriched, top_list, df


def build_theme_clusters(
    out_dir: Path,
    top_keywords: list[str],
    df: Counter,
    total_docs: int,
    theme_seeds: dict[str, list[str]] | dict[str, set[str]] | None,
) -> None:
    theme_seeds = theme_seeds or {}
    theme_order = list(theme_seeds.keys()) + ["其他"]
    buckets: dict[str, list[str]] = {k: [] for k in theme_order}

    for kw in top_keywords:
        assigned = False
        for theme, seeds in theme_seeds.items():
            if any(seed in kw or kw in seed for seed in seeds):
                buckets[theme].append(kw)
                assigned = True
                break
        if not assigned:
            buckets["其他"].append(kw)

    lines = ["# 主题聚类", ""]
    lines.append(f"- 文档数：{total_docs}")
    lines.append(f"- 关键词数：{len(top_keywords)}")
    lines.append("")
    for theme in theme_order:
        kws = buckets.get(theme) or []
        lines.append(f"## {theme}")
        lines.append("")
        if not kws:
            lines.append("- （暂无）")
            lines.append("")
            continue
        kws_sorted = sorted(kws, key=lambda k: (-df.get(k, 0), -len(k), k))
        for k in kws_sorted:
            lines.append(f"- {k} ({df.get(k, 0)})")
        lines.append("")

    (out_dir / "theme_clusters.md").write_text("\n".join(lines), encoding="utf-8")


def build_thought_graph(
    items: list[dict],
    out_dir: Path,
    top_keywords: int,
    top_models: int,
    top_values: int,
    top_styles: int,
    min_edge: int,
    max_edges: int,
) -> None:
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

    kw_list = top_by_counter(kw, top_keywords)
    model_list = top_by_counter(models, top_models)
    value_list = top_by_counter(values, top_values)
    style_list = top_by_counter(styles, top_styles)

    node_types = {}
    node_weight = {}
    for k in kw_list:
        node_types[k] = "keyword"
        node_weight[k] = kw[k]
    for k in model_list:
        node_types[k] = "model"
        node_weight[k] = models[k]
    for k in value_list:
        node_types[k] = "value"
        node_weight[k] = values[k]
    for k in style_list:
        node_types[k] = "style"
        node_weight[k] = styles[k]

    edges = Counter()
    for it in items:
        nodes = set()
        for k in it.get("keywords", []) or []:
            if k in node_types:
                nodes.add(k)
        for k in it.get("models", []) or []:
            if k in node_types:
                nodes.add(k)
        for k in it.get("values", []) or []:
            if k in node_types:
                nodes.add(k)
        for k in it.get("decision_style", []) or []:
            if k in node_types:
                nodes.add(k)
        nodes = sorted(nodes)
        for a, b in combinations(nodes, 2):
            key = (a, b) if a < b else (b, a)
            edges[key] += 1

    edge_list = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in edges.items()
        if w >= min_edge
    ]
    edge_list.sort(key=lambda x: (-x["weight"], x["source"], x["target"]))
    edge_list = edge_list[:max_edges]

    nodes = [
        {
            "id": k,
            "label": k,
            "type": node_types[k],
            "weight": node_weight[k],
        }
        for k in sorted(node_types.keys(), key=lambda x: (-node_weight[x], x))
    ]

    graph = {
        "nodes": nodes,
        "edges": edge_list,
        "meta": {
            "total_items": len(items),
            "top_keywords": top_keywords,
            "top_models": top_models,
            "top_values": top_values,
            "top_styles": top_styles,
            "min_edge": min_edge,
        },
    }

    (out_dir / "thought_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Mermaid
    mermaid = ["graph LR"]
    id_map = {n["id"]: f"n{idx}" for idx, n in enumerate(nodes)}
    for n in nodes:
        mermaid.append(f"  {id_map[n['id']]}[\"{sanitize_label(n['label'])}\"]")
    for e in edge_list:
        mermaid.append(
            f"  {id_map[e['source']]} -- {e['weight']} --> {id_map[e['target']]}"
        )
    (out_dir / "thought_graph.mmd").write_text("\n".join(mermaid), encoding="utf-8")

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


def build_relation_graph(
    items: list[dict],
    out_dir: Path,
    top_keywords: int,
    min_edge: int,
    max_edges: int,
) -> None:
    kw_counter = Counter()
    for it in items:
        for k in it.get("keywords", []) or []:
            kw_counter[k] += 1
    kw_list = top_by_counter(kw_counter, top_keywords)
    kw_set = set(kw_list)

    edges = Counter()
    node_weight = Counter()

    for it in items:
        text = it.get("text", "")
        for s in split_sentences(text):
            rel_types = detect_rel_types(s)
            if not rel_types:
                continue
            present = [k for k in kw_list if k in s]
            if len(present) < 2:
                continue
            for k in present:
                node_weight[k] += 1
            for a, b in combinations(sorted(set(present)), 2):
                for rel in rel_types:
                    edges[(a, b, rel)] += 1

    nodes = [
        {"id": k, "label": k, "type": "keyword", "weight": node_weight.get(k, 1)}
        for k in kw_list
    ]

    edge_list = [
        {"source": a, "target": b, "type": rel, "weight": w}
        for (a, b, rel), w in edges.items()
        if w >= min_edge
    ]
    edge_list.sort(
        key=lambda x: (-x["weight"], x["type"], x["source"], x["target"])
    )
    edge_list = edge_list[:max_edges]

    graph = {"nodes": nodes, "edges": edge_list}
    (out_dir / "relation_graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    mermaid = ["graph LR"]
    id_map = {k: f"n{idx}" for idx, k in enumerate(kw_list)}
    for k in kw_list:
        mermaid.append(f"  {id_map[k]}[\"{sanitize_label(k)}\"]")
    for e in edge_list:
        mermaid.append(
            f"  {id_map[e['source']]} -- {e['type']}:{e['weight']} --> {id_map[e['target']]}"
        )
    (out_dir / "relation_graph.mmd").write_text("\n".join(mermaid), encoding="utf-8")

    rel_groups = defaultdict(list)
    for e in edge_list:
        rel_groups[e["type"]].append(e)

    report = ["# 关系图谱摘要", ""]
    report.append(f"- 节点数：{len(nodes)}")
    report.append(f"- 边数：{len(edge_list)}")
    report.append("")
    for rel in sorted(rel_groups.keys()):
        edges_r = rel_groups[rel]
        report.append(f"## {rel} 关系")
        report.append("")
        for e in edges_r[:15]:
            report.append(f"- {e['source']} ↔ {e['target']} ({e['weight']})")
        report.append("")

    (out_dir / "relation_report.md").write_text("\n".join(report), encoding="utf-8")


def build_thought_hierarchy(
    items: list[dict],
    out_dir: Path,
    top_models: int,
    top_topics: int,
    belief_buckets: dict[str, list[str]] | dict[str, set[str]] | None,
    generic_terms: set[str],
    theme_seeds: dict[str, list[str]] | dict[str, set[str]] | None = None,
) -> None:
    model_counter = Counter()
    keyword_counter = Counter()
    for it in items:
        for m in it.get("models", []) or []:
            model_counter[m] += 1
        for k in it.get("keywords", []) or []:
            keyword_counter[k] += 1

    models = top_by_counter(model_counter, top_models)
    topics = [
        k
        for k in top_by_counter(keyword_counter, top_topics + 10)
        if k not in generic_terms
    ]
    topics = topics[:top_topics]

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

    belief_buckets = belief_buckets or {}
    theme_seeds = theme_seeds or {}
    if not belief_buckets:
        if theme_seeds:
            belief_buckets = {f"主题:{k}": set(v) for k, v in theme_seeds.items()}
        else:
            belief_buckets = {"核心主题": set(topics[:6])}

    belief_map: dict[str, list[str]] = {b: [] for b in belief_buckets}
    for m in models:
        assigned = False
        for belief, kws in belief_buckets.items():
            if m in kws or any(k in m for k in kws):
                belief_map[belief].append(m)
                assigned = True
                break
        if not assigned:
            belief_map.setdefault("其他框架", []).append(m)

    for belief, kws in belief_buckets.items():
        if belief_map.get(belief):
            continue
        for k in kws:
            if keyword_counter.get(k, 0) > 0:
                belief_map[belief].append(k)

    def pick_representatives(key: str, value: str, n: int = 3) -> list[dict]:
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

    def pick_by_any_keyword(keywords: set[str], n: int = 3) -> list[dict]:
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

    model_reps = {m: pick_representatives("models", m, n=3) for m in models}
    topic_reps = {t: pick_representatives("keywords", t, n=3) for t in topics}
    belief_reps = {
        belief: pick_by_any_keyword(set(kws), n=3)
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

    (out_dir / "thought_hierarchy.json").write_text(
        json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8"
    )

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


def build_argument_chains(items: list[dict], out_dir: Path, limit: int = 0) -> None:
    chains = []
    for it in items[: limit or None]:
        text = it.get("text", "")
        title = it.get("title", "")
        date = it.get("date", "")
        source_file = it.get("source_file", "")

        for para in split_paragraphs(text):
            sentences = split_sentences(para)
            last_claim = None
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                match = None
                for pat, rel in CAUSE_PATTERNS:
                    m = pat.match(s)
                    if m:
                        cause = m.group(1).strip()
                        effect = m.group(2).strip()
                        if cause and effect:
                            match = (rel, cause, effect)
                            break
                if match:
                    rel, cause, effect = match
                    last_claim = effect
                    chains.append(
                        {
                            "type": rel,
                            "cause": cause,
                            "conclusion": effect,
                            "evidence": "",
                            "source_file": source_file,
                            "title": title,
                            "date": date,
                        }
                    )
                    continue
                if any(m in s for m in EVIDENCE_MARKERS) and last_claim:
                    chains.append(
                        {
                            "type": "evidence",
                            "cause": "",
                            "conclusion": last_claim,
                            "evidence": s,
                            "source_file": source_file,
                            "title": title,
                            "date": date,
                        }
                    )

    jsonl_path = out_dir / "argument_chains.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for c in chains:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    md_lines = ["# 论证链摘要", "", f"- 链条数：{len(chains)}", ""]
    for c in chains[:30]:
        if c["type"] == "evidence":
            md_lines.append(f"- [证据] {c['evidence']} → 支持：{c['conclusion']}")
        else:
            md_lines.append(f"- [{c['type']}] 因：{c['cause']} → 结：{c['conclusion']}")
    (out_dir / "argument_chains.md").write_text("\n".join(md_lines), encoding="utf-8")


def build_node_weights(
    items: list[dict],
    out_dir: Path,
    belief_buckets: dict[str, list[str]] | dict[str, set[str]] | None,
    generic_terms: set[str],
) -> None:
    topic_counter = Counter()
    model_counter = Counter()

    for it in items:
        for k in it.get("keywords", []) or []:
            if k not in generic_terms:
                topic_counter[k] += 1
        for m in it.get("models", []) or []:
            model_counter[m] += 1

    belief_counter = Counter()
    for belief, kws in (belief_buckets or {}).items():
        kws_set = set(kws)
        for it in items:
            if set(it.get("keywords", []) or []) & kws_set:
                belief_counter[belief] += 1

    weights = {
        "beliefs": normalize(belief_counter),
        "models": normalize(model_counter),
        "topics": normalize(topic_counter),
        "raw_counts": {
            "beliefs": dict(belief_counter),
            "models": dict(model_counter),
            "topics": dict(topic_counter),
        },
    }

    (out_dir / "node_weights.json").write_text(
        json.dumps(weights, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# -------------------------
# Main
# -------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", required=True, help="persona slug")
    parser.add_argument("--input", required=True, help="plain_text folder")
    parser.add_argument("--out", required=True, help="output dir")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--top-keywords", type=int, default=60)
    parser.add_argument("--top-models", type=int, default=20)
    parser.add_argument("--top-values", type=int, default=12)
    parser.add_argument("--top-styles", type=int, default=12)
    parser.add_argument("--top-keywords-rel", type=int, default=40)
    parser.add_argument("--max-keywords-per-doc", type=int, default=16)
    parser.add_argument("--min-edge", type=int, default=3)
    parser.add_argument("--max-edges", type=int, default=180)
    args = parser.parse_args()

    cfg = load_config(args.config)
    cleanup_patterns = cfg.get("cleanup_patterns", [])
    belief_buckets = cfg.get("belief_buckets", {}) or {}
    theme_seeds = cfg.get("theme_seeds", {}) or {}
    generic_terms = set(cfg.get("generic_terms", []))
    model_terms = cfg.get("model_terms", []) or []
    value_terms = cfg.get("value_terms", []) or []
    style_terms = cfg.get("style_terms", []) or []
    top_terms = cfg.get("top_terms", []) or []
    language_markers = cfg.get("language_markers", []) or []

    seed_keywords: list[str] = []
    seed_keywords.extend(top_terms)
    seed_keywords.extend(model_terms)
    seed_keywords.extend(value_terms)
    seed_keywords.extend(style_terms)
    seed_keywords.extend(language_markers)
    for seeds in theme_seeds.values():
        seed_keywords.extend(list(seeds))
    seed_keywords = sorted({s for s in seed_keywords if s})

    plain_dir = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = sorted(plain_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"no plain_text files found in {plain_dir}")

    raw_items = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = clean_text(text, cleanup_patterns)
        raw_items.append(
            {
                "title": extract_title(text),
                "date": parse_date_from_filename(path.name),
                "source_file": path.name,
                "text": text,
            }
        )

    extracted, top_keywords, df = build_extractions(
        raw_items,
        top_keywords=args.top_keywords,
        max_keywords_per_doc=args.max_keywords_per_doc,
        seed_keywords=seed_keywords,
        model_terms=model_terms,
        value_terms=value_terms,
        style_terms=style_terms,
    )

    # Add text back for downstream builders
    items = []
    for it_raw, it_ext in zip(raw_items, extracted):
        it_ext["text"] = it_raw["text"]
        items.append(it_ext)

    build_theme_clusters(
        out_dir, top_keywords, df, total_docs=len(items), theme_seeds=theme_seeds
    )

    build_thought_graph(
        items,
        out_dir,
        top_keywords=args.top_keywords,
        top_models=args.top_models,
        top_values=args.top_values,
        top_styles=args.top_styles,
        min_edge=args.min_edge,
        max_edges=args.max_edges,
    )

    build_relation_graph(
        items,
        out_dir,
        top_keywords=args.top_keywords_rel,
        min_edge=args.min_edge,
        max_edges=args.max_edges,
    )

    build_thought_hierarchy(
        items,
        out_dir,
        top_models=args.top_models,
        top_topics=10,
        belief_buckets=belief_buckets,
        generic_terms=generic_terms,
        theme_seeds=theme_seeds,
    )

    build_argument_chains(items, out_dir)
    build_node_weights(items, out_dir, belief_buckets, generic_terms)

    logger.info(f"[done] persona={args.persona} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
