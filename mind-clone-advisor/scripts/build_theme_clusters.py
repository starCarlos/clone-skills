#!/usr/bin/env python3
"""Build theme clusters from extraction JSONL.

Uses domain_config.json for theme seeds. Insights are generated dynamically
rather than hardcoded.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np

from domain_config import load_config
from topic_model import build_tfidf, display_term, lsa_topics, tokenize
from utils import LABEL_NOISE, load_jsonl, strip_front_matter, sample_text, setup_logging

logger = setup_logging(__name__)


def sample_titles(docs, n=5):
    docs = [
        d
        for d in docs
        if (d.get("title") and d.get("title") != "---") or d.get("source_file")
    ]
    docs.sort(key=lambda d: d.get("date") or "")
    if not docs:
        return []
    step = max(1, len(docs) // n)
    titles = []
    for i in range(0, len(docs), step):
        title = docs[i].get("title")
        if title == "---":
            title = ""
        titles.append(title or docs[i].get("source_file") or "")
    return titles[:n]


def top_keywords(docs, seeds=None, n=8):
    c = Counter()
    for d in docs:
        text = d.get("_tm_text", "")
        for tok in tokenize(text):
            if seeds and tok not in seeds:
                continue
            c[tok] += 1
    if not c and seeds:
        for d in docs:
            text = d.get("_tm_text", "")
            for tok in tokenize(text):
                c[tok] += 1
    return [display_term(k) for k, _ in c.most_common(n)]


def load_doc_text(it: dict, kb_dir: Path, limit: int = 12000) -> str:
    src = it.get("source_file") or ""
    if src and kb_dir.exists():
        p = kb_dir / src
        if p.exists():
            raw = p.read_text(encoding="utf-8", errors="ignore")
            raw = strip_front_matter(raw)
            if "shareholder_letter" in src or "owners_manual" in src:
                return sample_text(raw, 12000)
            return sample_text(raw, limit)
    return it.get("core_view", "") or ""


def _make_cluster_label(seed: str, kws: list[str], docs: list) -> str:
    """Create a descriptive cluster label from keywords and representative titles.

    Avoids using raw TF-IDF tokens (e.g. 'actually', 'going') as headers.
    Combines the top 2-3 most meaningful keywords, filtering stopword-like terms.
    """
    # Gather meaningful terms from keywords
    meaningful = []
    for kw in kws:
        kw_lower = kw.lower().strip()
        if kw_lower not in LABEL_NOISE and len(kw_lower) > 2:
            meaningful.append(kw)
        if len(meaningful) >= 3:
            break

    # If seed itself is meaningful, include it
    if seed.lower() not in LABEL_NOISE and len(seed) > 2 and seed not in meaningful:
        meaningful.insert(0, seed)

    if not meaningful:
        # Fallback: use first representative title (truncated)
        for d in docs[:1]:
            title = d.get("title") or d.get("source_file") or ""
            if title and title != "---":
                return title[:60]
        return seed

    # Combine top terms into a readable label
    return " / ".join(meaningful[:3])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--out", required=True, help="output md path")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    theme_seeds = cfg.get("theme_seeds", {})
    generic_terms = set(cfg.get("generic_terms", []))
    domain_phrases = cfg.get("phrases", {}) or None

    items = load_jsonl(Path(args.input))
    if not items:
        raise SystemExit("no items")

    skill_dir = Path(args.input).resolve().parent.parent
    kb_dir = skill_dir / "kb" / "plain_text"

    docs = []
    for it in items:
        title = it.get("title") or ""
        core = load_doc_text(it, kb_dir)
        it["_tm_text"] = f"{title}\n{core}"
        docs.append(it["_tm_text"])

    tfidf, vocab, _ = build_tfidf(docs, min_df=2, max_df_ratio=0.6, max_features=4000, phrases=domain_phrases)
    topic_terms, doc_topics = lsa_topics(tfidf, vocab, num_topics=6, top_n=8)

    if not theme_seeds:
        # Auto topics when no domain config exists
        theme_seeds = {f"主题{i+1}": terms for i, terms in enumerate(topic_terms)}

    # Normalize seeds to tokens
    norm_seeds = {}
    for theme, kws in theme_seeds.items():
        tokens = set()
        for k in kws:
            tokens.update(tokenize(k))
        norm_seeds[theme] = tokens

    topic_to_theme: dict[int, str] = {}
    for idx, terms in enumerate(topic_terms):
        best_theme = None
        best_score = -1
        term_set = set(terms)
        for theme, seeds in norm_seeds.items():
            score = len(term_set.intersection(seeds))
            if score > best_score:
                best_score = score
                best_theme = theme
        if best_theme:
            topic_to_theme[idx] = best_theme

    index = {t: i for i, t in enumerate(vocab)}
    theme_vectors = {}
    for theme, seeds in norm_seeds.items():
        vec = np.zeros((len(vocab),), dtype=np.float64)
        for s in seeds:
            if s in index and s not in generic_terms:
                vec[index[s]] = 1.0
        if vec.sum() > 0:
            vec = vec / np.linalg.norm(vec)
            theme_vectors[theme] = vec

    doc_theme = []
    for i in range(len(items)):
        if tfidf.shape[1] == 0 or not theme_vectors:
            doc_theme.append("其他")
            continue
        scores = {t: float(tfidf[i].dot(v)) for t, v in theme_vectors.items()}
        best_theme = max(scores.items(), key=lambda x: x[1])[0]
        if scores[best_theme] <= 0:
            if doc_topics.shape[1] > 0:
                topic_idx = int(abs(doc_topics[i]).argmax())
                best_theme = topic_to_theme.get(topic_idx, best_theme)
        doc_theme.append(best_theme)

    clusters = {k: [] for k in theme_seeds}
    clusters["其他"] = []
    for i, it in enumerate(items):
        clusters.get(doc_theme[i], clusters["其他"]).append(it)

    lines = []
    lines.append("# 主题聚类")
    lines.append("")
    lines.append(f"- 总文章数：{len(items)}")
    lines.append("")

    for theme, docs in clusters.items():
        if not docs:
            continue
        kws = top_keywords(docs, seeds=norm_seeds.get(theme))
        # Generate a descriptive header from top keywords instead of raw seed term
        header = _make_cluster_label(theme, kws, docs)
        lines.append(f"## {header}")
        lines.append("")
        lines.append(f"- 覆盖篇数：{len(docs)}")
        if kws:
            lines.append(f"- 高频词：{'、'.join(kws)}")
        # No hardcoded insights - just show representative titles
        samples = sample_titles(docs, n=5)
        if samples:
            lines.append("- 代表标题：")
            for t in samples:
                lines.append(f"  - {t}")
        lines.append("")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"[done] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
