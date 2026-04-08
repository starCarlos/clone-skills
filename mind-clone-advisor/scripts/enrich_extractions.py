#!/usr/bin/env python3
"""Backfill missing extraction fields using current heuristics and persona priors."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from domain_config import load_config
from llm_extract import (
    DEFAULT_MODEL_FALLBACK,
    DEFAULT_VALUE_FALLBACK,
    clean_text,
    extract_decision_style,
    extract_models,
    extract_values,
    infer_blindspots,
    language_fingerprint,
    top_keywords,
)
from utils import load_jsonl, strip_front_matter, setup_logging

logger = setup_logging(__name__)

MEANINGLESS_KEYWORD_TERMS = {
    "thing",
    "things",
    "lot",
    "lots",
    "don",
    "said",
    "say",
    "course",
    "really",
    "going",
    "good",
    "make",
    "money",
    "people",
    "company",
    "companies",
    "business",
}


def is_meaningful_term(term: str, generic_terms: set[str]) -> bool:
    value = (term or "").strip()
    if not value:
        return False
    lower = value.lower()
    if lower in MEANINGLESS_KEYWORD_TERMS or lower in generic_terms:
        return False
    if re.fullmatch(r"[a-z]{1,3}", lower):
        return False
    if re.fullmatch(r"[\u4e00-\u9fff]{1,2}", value):
        return False
    return True


def choose_top(counter: Counter, limit: int) -> list[str]:
    return [key for key, _ in counter.most_common(limit)]


def load_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def derive_priors(items: list[dict], summary: dict) -> dict[str, list[str]]:
    models = Counter()
    values = Counter()
    styles = Counter()
    blindspots = Counter()
    keywords = Counter()

    for item in items:
        for key in item.get("models") or []:
            models[key] += 1
        for key in item.get("values") or []:
            values[key] += 1
        for key in item.get("decision_style") or []:
            styles[key] += 1
        for key in item.get("blindspots") or []:
            blindspots[key] += 1
        for key in item.get("keywords") or []:
            keywords[key] += 1

    return {
        "top_models": summary.get("top_models") or choose_top(models, 12),
        "top_values": summary.get("top_values") or choose_top(values, 10),
        "top_decision_style": summary.get("top_decision_style") or choose_top(styles, 8),
        "top_blindspots": summary.get("top_blindspots") or choose_top(blindspots, 6),
        "top_keywords": summary.get("top_keywords") or choose_top(keywords, 20),
    }


def load_body(skill_dir: Path, item: dict, cleanup_patterns: list[str]) -> str:
    source_file = (item.get("source_file") or "").strip()
    for candidate_dir in (
        skill_dir / "kb" / "plain_text.filtered",
        skill_dir / "kb" / "plain_text",
    ):
        candidate = candidate_dir / source_file
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8", errors="ignore")
            text = strip_front_matter(text)
            title = (item.get("title") or "").strip()
            if title and title in text:
                text = text.replace(title, "", 1).strip()
            return clean_text(text, cleanup_patterns)

    fallback_parts = [
        item.get("title", ""),
        item.get("core_view", ""),
        " ".join(item.get("stances") or []),
    ]
    for anchor in item.get("evidence_anchors") or []:
        if anchor.get("text"):
            fallback_parts.append(anchor["text"])
    return clean_text(" ".join(part for part in fallback_parts if part), cleanup_patterns)


def dedupe_keep_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def fallback_blindspots(
    text: str,
    priors: dict[str, list[str]],
    top_terms: list[str],
    theme_seeds: dict[str, list[str]],
    generic_terms: set[str],
) -> list[str]:
    active_theme_seeds = theme_seeds if len(theme_seeds) >= 2 else None
    blindspots = infer_blindspots(text, top_terms, theme_seeds=active_theme_seeds)
    if blindspots:
        return blindspots[:5]

    prior_blindspots = priors.get("top_blindspots") or []
    if prior_blindspots:
        return prior_blindspots[:3]

    candidates = []
    for term in priors.get("top_keywords") or top_terms:
        if not is_meaningful_term(term, generic_terms):
            continue
        if term in text:
            continue
        candidates.append(f"未涉及「{term}」相关主题")
        if len(candidates) >= 3:
            break
    return candidates


def maybe_fill_with_priors(
    current: list[str],
    derived: list[str],
    priors: list[str],
    total_docs: int,
    max_docs_for_priors: int,
    limit: int,
) -> list[str]:
    if current:
        return current
    if derived:
        return derived[:limit]
    if total_docs <= max_docs_for_priors:
        return priors[:limit]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument(
        "--max-docs-for-priors",
        type=int,
        default=200,
        help="only use persona-level priors for smaller corpora",
    )
    parser.add_argument("--out", default="", help="optional explicit output path")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    ext_path = skill_dir / "analysis" / "extractions.jsonl"
    if not ext_path.exists():
        raise SystemExit(f"missing extractions: {ext_path}")

    items = load_jsonl(ext_path)
    if not items:
        raise SystemExit(f"no items in {ext_path}")

    config_path = skill_dir / "analysis" / "domain_config.json"
    cfg = load_config(str(config_path) if config_path.exists() else None)
    summary = load_summary(skill_dir / "analysis" / "corpus_summary.json")
    priors = derive_priors(items, summary)
    total_docs = len(items)

    top_terms = list(dict.fromkeys((summary.get("top_keywords") or []) + cfg.get("top_terms", [])))
    model_keywords = list(
        dict.fromkeys((summary.get("top_models") or []) + cfg.get("model_terms", []) + DEFAULT_MODEL_FALLBACK)
    )
    value_keywords = list(
        dict.fromkeys((summary.get("top_values") or []) + cfg.get("value_terms", []) + DEFAULT_VALUE_FALLBACK)
    )
    language_markers = cfg.get("language_markers", [])
    cleanup_patterns = cfg.get("cleanup_patterns", [])
    theme_seeds = cfg.get("theme_seeds", {})
    generic_terms = {str(term).lower() for term in (cfg.get("generic_terms") or [])}

    changed = 0
    field_updates = Counter()
    enriched_items: list[dict] = []

    for item in items:
        body = load_body(skill_dir, item, cleanup_patterns)
        merged_text = " ".join(
            [
                item.get("title", ""),
                body,
                item.get("core_view", ""),
                " ".join(item.get("stances") or []),
            ]
        )

        derived_keywords = top_keywords(body or merged_text, top_terms, top_k=12)
        derived_models = extract_models(merged_text, model_keywords)
        derived_values = extract_values(merged_text, value_keywords)
        derived_styles = extract_decision_style(merged_text)
        derived_language = language_fingerprint(body or merged_text, top_terms, language_markers)
        derived_blindspots = fallback_blindspots(
            merged_text,
            priors=priors,
            top_terms=top_terms,
            theme_seeds=theme_seeds,
            generic_terms=generic_terms,
        )

        updated = dict(item)

        new_keywords = dedupe_keep_order((updated.get("keywords") or []) or derived_keywords)
        if new_keywords != (updated.get("keywords") or []):
            updated["keywords"] = new_keywords
            field_updates["keywords"] += 1

        new_models = dedupe_keep_order(
            maybe_fill_with_priors(
                updated.get("models") or [],
                derived_models,
                priors.get("top_models") or [],
                total_docs=total_docs,
                max_docs_for_priors=args.max_docs_for_priors,
                limit=2,
            )
        )
        if new_models != (updated.get("models") or []):
            updated["models"] = new_models
            field_updates["models"] += 1

        new_values = dedupe_keep_order(
            maybe_fill_with_priors(
                updated.get("values") or [],
                derived_values,
                priors.get("top_values") or [],
                total_docs=total_docs,
                max_docs_for_priors=args.max_docs_for_priors,
                limit=2,
            )
        )
        if new_values != (updated.get("values") or []):
            updated["values"] = new_values
            field_updates["values"] += 1

        new_styles = dedupe_keep_order(
            maybe_fill_with_priors(
                updated.get("decision_style") or [],
                derived_styles,
                priors.get("top_decision_style") or [],
                total_docs=total_docs,
                max_docs_for_priors=args.max_docs_for_priors,
                limit=2,
            )
        )
        if new_styles != (updated.get("decision_style") or []):
            updated["decision_style"] = new_styles
            field_updates["decision_style"] += 1

        new_language = dedupe_keep_order((updated.get("language_fingerprint") or []) or derived_language)
        if new_language != (updated.get("language_fingerprint") or []):
            updated["language_fingerprint"] = new_language
            field_updates["language_fingerprint"] += 1

        new_blindspots = dedupe_keep_order((updated.get("blindspots") or []) or derived_blindspots)
        if new_blindspots != (updated.get("blindspots") or []):
            updated["blindspots"] = new_blindspots
            field_updates["blindspots"] += 1

        if updated != item:
            changed += 1
        enriched_items.append(updated)

    out_path = Path(args.out) if args.out else ext_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for item in enriched_items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    logger.info(
        "[done] enriched=%d/%d path=%s updates=%s",
        changed,
        total_docs,
        out_path,
        dict(field_updates),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
