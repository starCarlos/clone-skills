#!/usr/bin/env python3
"""Add evidence_anchors to extractions.jsonl from plain_text (generic)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domain_config import load_config
from utils import extract_title, split_sentences, validate_path_safe, setup_logging

logger = setup_logging(__name__)


BAD_MARKERS = [
    "公众号",
    "广告",
    "二维码",
    "扫码",
    "关注",
    "转载",
    "免责声明",
    "点击",
    "链接",
    "http",
    "https",
    "www.",
    "阅读原文",
]

CLAIM_MARKERS = [
    "我认为",
    "我觉得",
    "关键是",
    "核心是",
    "本质是",
    "结论是",
    "应该",
    "必须",
    "不要",
    "优先",
    "所以",
    "因此",
    "这意味着",
    # English
    "we believe",
    "we think",
    "our view",
    "the key is",
    "the core is",
    "the point is",
    "therefore",
    "thus",
    "this means",
    "which means",
]

CAUSE_MARKERS = [
    "因为",
    "所以",
    "因此",
    "导致",
    "本质",
    "because",
    "therefore",
    "thus",
    "as a result",
    "leads to",
    "results in",
]



def clean_text(text: str, cleanup_patterns: list[str]) -> str:
    for pat in cleanup_patterns:
        text = text.replace(pat, "")
    return text



def valid_sentence(s: str) -> bool:
    if len(s) < 12 or len(s) > 180:
        return False
    if any(b in s for b in BAD_MARKERS):
        return False
    return True


def score_sentence(s: str, keywords: list[str]) -> tuple[int, list[str]]:
    hits = [k for k in keywords if k and k in s]
    score = len(hits) * 10
    if any(m in s for m in CLAIM_MARKERS):
        score += 4
    if any(m in s for m in CAUSE_MARKERS):
        score += 2
    return score, hits


def build_anchors(text: str, keywords: list[str], limit: int = 6) -> list[dict]:
    anchors = []
    seen = set()
    for s in split_sentences(text):
        if not valid_sentence(s):
            continue
        score, hits = score_sentence(s, keywords)
        if not hits:
            continue
        key = s.strip()
        if key in seen:
            continue
        seen.add(key)
        anchors.append({"text": s, "keywords": hits, "score": score})
    if not anchors:
        for s in split_sentences(text):
            if not valid_sentence(s):
                continue
            score = 0
            if any(m in s for m in CLAIM_MARKERS):
                score += 6
            if any(m in s for m in CAUSE_MARKERS):
                score += 3
            if 20 <= len(s) <= 90:
                score += 2
            if score == 0:
                continue
            key = s.strip()
            if key in seen:
                continue
            seen.add(key)
            anchors.append({"text": s, "keywords": [], "score": score})
    if not anchors:
        for s in split_sentences(text):
            if not valid_sentence(s):
                continue
            if not (30 <= len(s) <= 140):
                continue
            key = s.strip()
            if key in seen:
                continue
            seen.add(key)
            anchors.append({"text": s, "keywords": [], "score": 1})
    # final fallback: take first short sentences to guarantee coverage
    if not anchors:
        for s in split_sentences(text):
            s = s.strip()
            if len(s) < 10:
                continue
            if any(b in s for b in BAD_MARKERS):
                continue
            key = s
            if key in seen:
                continue
            seen.add(key)
            anchors.append({"text": s, "keywords": [], "score": 1})
            if len(anchors) >= limit:
                break
    anchors.sort(key=lambda x: x["score"], reverse=True)
    return [{"text": a["text"], "keywords": a["keywords"]} for a in anchors[:limit]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain-text-dir", required=True)
    parser.add_argument("--input", required=True, help="extractions.jsonl")
    parser.add_argument("--output", required=True, help="output jsonl")
    parser.add_argument("--config", default=None, help="domain_config.json path")
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()

    cfg = load_config(args.config)
    cleanup_patterns = cfg.get("cleanup_patterns", [])

    plain_dir = Path(args.plain_text_dir)
    items = []
    with Path(args.input).open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            items.append(json.loads(line))

    updated = []
    for it in items:
        src = it.get("source_file", "")
        validate_path_safe(plain_dir, src)
        path = plain_dir / src
        if not path.exists():
            updated.append(it)
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(text)
        body = text.replace(title, "", 1).strip() if title else text
        body = clean_text(body, cleanup_patterns)

        keywords = it.get("keywords", []) or []
        anchors = build_anchors(body, keywords, limit=args.limit)
        it["evidence_anchors"] = anchors
        updated.append(it)

    Path(args.output).write_text(
        "\n".join(json.dumps(it, ensure_ascii=False) for it in updated) + "\n",
        encoding="utf-8",
    )
    logger.info(f"[done] output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
