#!/usr/bin/env python3
"""Discover domain-specific keywords, themes, beliefs from any plain_text corpus.

Outputs domain_config.json that all other mind-clone scripts consume.
No hardcoded domain assumptions — everything is derived from the corpus.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from domain_config import (
    MODEL_SUFFIXES,
    STOPWORDS_CJK,
    STOPWORDS_EN,
    STYLE_WORDS,
    VALUE_SUFFIXES,
)
from utils import LABEL_NOISE, setup_logging

logger = setup_logging(__name__)

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


def iter_cjk_ngrams(text: str, min_n: int = 2, max_n: int = 4) -> list[str]:
    out: list[str] = []
    for seq in CJK_RE.findall(text):
        if len(seq) < min_n:
            continue
        upper = min(max_n, len(seq))
        for n in range(min_n, upper + 1):
            for i in range(len(seq) - n + 1):
                token = seq[i : i + n]
                if token in STOPWORDS_CJK or len(set(token)) == 1:
                    continue
                out.append(token)
    return out


def iter_en_words(text: str) -> list[str]:
    return [w.lower() for w in EN_RE.findall(text) if w.lower() not in STOPWORDS_EN]


def extract_tokens(text: str) -> list[str]:
    return iter_cjk_ngrams(text) + iter_en_words(text)


# ---------------------------------------------------------------------------
# Boilerplate / cleanup detection
# ---------------------------------------------------------------------------


def detect_cleanup_patterns(docs: list[str], threshold: float = 0.20) -> list[str]:
    """Find exact short strings that appear in >threshold fraction of docs."""
    n_docs = len(docs)
    if n_docs == 0:
        return []
    line_counts: Counter[str] = Counter()
    for text in docs:
        seen = set()
        for line in text.splitlines():
            line = line.strip()
            if 4 < len(line) < 80 and line not in seen:
                seen.add(line)
                line_counts[line] += 1
    return [
        line
        for line, cnt in line_counts.most_common(20)
        if cnt / n_docs >= threshold
    ]


# ---------------------------------------------------------------------------
# Language marker detection
# ---------------------------------------------------------------------------


def detect_language_markers(docs: list[str], top_n: int = 15) -> list[str]:
    """Find recurring short phrases unique to this corpus (high DF)."""
    n_docs = len(docs)
    if n_docs == 0:
        return []
    phrase_df: Counter[str] = Counter()
    # CJK markers: 4-8 char CJK phrases with high document frequency
    for text in docs:
        seen = set()
        for seq in CJK_RE.findall(text):
            for length in range(4, min(9, len(seq) + 1)):
                for i in range(len(seq) - length + 1):
                    phrase = seq[i : i + length]
                    if phrase not in STOPWORDS_CJK and phrase not in seen:
                        seen.add(phrase)
                        phrase_df[phrase] += 1
    # English markers: 2-3 word phrases with high document frequency
    for text in docs:
        seen: set[str] = set()
        words = EN_RE.findall(text.lower())
        for i in range(len(words) - 1):
            for n in (2, 3):
                if i + n > len(words):
                    break
                phrase = " ".join(words[i : i + n])
                if len(phrase) >= 8 and phrase not in STOPWORDS_EN and phrase not in seen:
                    seen.add(phrase)
                    phrase_df[phrase] += 1
    # Want phrases that appear in many docs but not all (signature-like)
    markers = []
    for phrase, df in phrase_df.most_common(200):
        ratio = df / n_docs
        if 0.05 <= ratio <= 0.60 and df >= 3:
            markers.append(phrase)
        if len(markers) >= top_n:
            break
    return markers


# ---------------------------------------------------------------------------
# TF-IDF keyword discovery
# ---------------------------------------------------------------------------


def discover_keywords(
    docs: list[str],
    top_n: int = 80,
    min_df: int = 2,
) -> tuple[list[str], Counter, dict[str, float]]:
    """Return top keywords by TF-IDF, along with DF counts and scores."""
    n_docs = len(docs)
    if n_docs == 0:
        return [], Counter(), {}

    tf_total: Counter[str] = Counter()
    df: Counter[str] = Counter()

    for text in docs:
        tokens = extract_tokens(text)
        tf_total.update(tokens)
        unique = set(tokens)
        df.update(unique)

    # TF-IDF
    scores: dict[str, float] = {}
    for token, freq in tf_total.items():
        if df[token] < min_df:
            continue
        if any(ch.isdigit() for ch in token):
            continue
        idf = math.log(n_docs / (1 + df[token]))
        scores[token] = freq * idf

    ranked = sorted(scores.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
    top_terms = [t for t, _ in ranked[:top_n]]
    return top_terms, df, scores


# ---------------------------------------------------------------------------
# Classify keywords into model / value / style
# ---------------------------------------------------------------------------


def classify_terms(
    terms: list[str],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Classify terms into model_terms, value_terms, style_terms, generic_terms."""
    model_terms = []
    value_terms = []
    style_terms = []
    generic = []

    for t in terms:
        if t.endswith(MODEL_SUFFIXES):
            model_terms.append(t)
        elif t.endswith(VALUE_SUFFIXES):
            value_terms.append(t)
        elif t in STYLE_WORDS:
            style_terms.append(t)
        else:
            generic.append(t)

    return model_terms, value_terms, style_terms, generic


# ---------------------------------------------------------------------------
# Co-occurrence clustering → belief buckets & theme seeds
# ---------------------------------------------------------------------------


def build_cooccurrence(
    docs: list[str], vocab: set[str], min_co: int = 3
) -> dict[str, Counter]:
    co: dict[str, Counter] = defaultdict(Counter)
    for text in docs:
        tokens = set(extract_tokens(text)) & vocab
        for a, b in combinations(sorted(tokens), 2):
            co[a][b] += 1
            co[b][a] += 1
    # Prune weak edges
    for k in list(co.keys()):
        co[k] = Counter({t: c for t, c in co[k].items() if c >= min_co})
        if not co[k]:
            del co[k]
    return dict(co)


def cluster_keywords(
    co: dict[str, Counter], terms: list[str], max_clusters: int = 8, min_size: int = 2
) -> dict[str, list[str]]:
    """Simple greedy clustering: pick highest-degree node, absorb neighbors."""
    remaining = set(terms)
    degree = Counter()
    for k, neighbors in co.items():
        if k in remaining:
            degree[k] = sum(neighbors.values())

    clusters: dict[str, list[str]] = {}
    for seed, _ in degree.most_common():
        if seed not in remaining:
            continue
        if len(clusters) >= max_clusters:
            break
        neighbors = co.get(seed, {})
        group = [seed]
        # Add top co-occurring neighbors
        for neighbor, _ in Counter(neighbors).most_common(6):
            if neighbor in remaining and neighbor != seed:
                group.append(neighbor)
                remaining.discard(neighbor)
        remaining.discard(seed)
        if len(group) >= min_size:
            key = _make_theme_key(group)
            if key in clusters:
                key = f"{key} ({seed})"
            clusters[key] = group

    return clusters


def _make_theme_key(group: list[str], max_terms: int = 3) -> str:
    """Generate a readable theme key from a group of co-occurring terms.

    Filters out stopword-like noise tokens and combines the top meaningful terms.
    """
    meaningful = [t for t in group if t.lower() not in LABEL_NOISE and len(t) > 2]
    if meaningful:
        return " / ".join(meaningful[:max_terms])
    # Fallback to first term
    return group[0] if group else "other"


def discover_themes(
    co: dict[str, Counter], terms: list[str], max_themes: int = 10
) -> dict[str, list[str]]:
    """Discover theme groups from co-occurrence (broader clusters)."""
    remaining = set(terms)
    degree = Counter()
    for k, neighbors in co.items():
        if k in remaining:
            degree[k] = sum(neighbors.values())

    themes: dict[str, list[str]] = {}
    for seed, _ in degree.most_common():
        if seed not in remaining:
            continue
        if len(themes) >= max_themes:
            break
        neighbors = co.get(seed, {})
        group = [seed]
        for neighbor, _ in Counter(neighbors).most_common(10):
            if neighbor in remaining and neighbor != seed:
                group.append(neighbor)
                remaining.discard(neighbor)
        remaining.discard(seed)
        if len(group) >= 2:
            key = _make_theme_key(group)
            # Avoid duplicate keys
            if key in themes:
                key = f"{key} ({seed})"
            themes[key] = group

    return themes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover domain config from a plain_text corpus."
    )
    parser.add_argument("--input", required=True, help="plain_text folder")
    parser.add_argument("--person", default="", help="person display name")
    parser.add_argument("--out", required=True, help="output domain_config.json path")
    parser.add_argument("--top-keywords", type=int, default=80)
    parser.add_argument("--max-clusters", type=int, default=8)
    parser.add_argument("--max-themes", type=int, default=10)
    parser.add_argument("--min-df", type=int, default=2)
    args = parser.parse_args()

    input_dir = Path(args.input)
    paths = sorted(input_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"no .md files found in {input_dir}")

    docs = [p.read_text(encoding="utf-8", errors="ignore") for p in paths]
    logger.info(f"[info] loaded {len(docs)} documents from {input_dir}")

    # 1. Keyword discovery
    top_terms, df, scores = discover_keywords(
        docs, top_n=args.top_keywords, min_df=args.min_df
    )
    logger.info(f"[info] discovered {len(top_terms)} top keywords")

    # 2. Classify
    model_terms, value_terms, style_terms, generic_terms = classify_terms(top_terms)
    logger.info(
        f"[info] classified: models={len(model_terms)}, values={len(value_terms)}, "
        f"styles={len(style_terms)}, generic={len(generic_terms)}"
    )

    # 3. Co-occurrence analysis
    vocab = set(top_terms)
    co = build_cooccurrence(docs, vocab, min_co=max(2, len(docs) // 50))
    logger.info(f"[info] co-occurrence graph: {len(co)} nodes")

    # 4. Belief buckets (tight clusters)
    belief_buckets = cluster_keywords(co, top_terms, max_clusters=args.max_clusters)
    logger.info(f"[info] discovered {len(belief_buckets)} belief buckets")

    # 5. Theme seeds (broader clusters)
    theme_seeds = discover_themes(co, top_terms, max_themes=args.max_themes)
    logger.info(f"[info] discovered {len(theme_seeds)} theme clusters")

    # 6. Cleanup patterns
    cleanup_patterns = detect_cleanup_patterns(docs)
    logger.info(f"[info] detected {len(cleanup_patterns)} cleanup patterns")

    # 7. Language markers
    language_markers = detect_language_markers(docs)
    logger.info(f"[info] detected {len(language_markers)} language markers")

    # 8. Identify overly generic terms (appear in >80% of docs)
    n_docs = len(docs)
    overly_generic = [t for t in top_terms if df.get(t, 0) / n_docs > 0.80]

    config = {
        "person": args.person,
        "top_terms": top_terms,
        "model_terms": model_terms,
        "value_terms": value_terms,
        "style_terms": style_terms,
        "belief_buckets": belief_buckets,
        "theme_seeds": theme_seeds,
        "language_markers": language_markers,
        "cleanup_patterns": cleanup_patterns,
        "generic_terms": overly_generic,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"[done] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
