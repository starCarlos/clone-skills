#!/usr/bin/env python3
"""Build evidence_anchors.md from analysis/extractions.jsonl.

Aggregates anchor snippets with basic filtering and de-duplication.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from topic_model import tokenize
from utils import load_jsonl, strip_front_matter, sample_text, setup_logging

logger = setup_logging(__name__)

SKIP_PATTERNS = [
    r"laughter",
    r"laughs",
    r"applause",
    r"^\s*http",
    r"dark mode toggle",
    r"see all posts",
]


def is_bad(text: str) -> bool:
    if "http" in text.lower():
        return True
    for pat in SKIP_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            return True
    return False


def extract_sentences(text: str, limit: int = 2) -> list[str]:
    text = strip_front_matter(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[。！？.!?])\s+", text)
    results = []
    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        if is_bad(s):
            continue
        if len(s) < 40 or len(s) > 260:
            continue
        if len(tokenize(s)) < 3:
            continue
        results.append(s)
        if len(results) >= limit:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="analysis/extractions.jsonl")
    parser.add_argument("--out", required=True, help="output evidence_anchors.md")
    parser.add_argument("--limit", type=int, default=40, help="max anchors")
    args = parser.parse_args()

    items = load_jsonl(Path(args.input))
    if not items:
        raise SystemExit("no items")

    anchors = []
    base_dir = Path(args.input).resolve().parent.parent
    kb_dir = base_dir / "kb" / "plain_text"

    def load_doc_text(it: dict) -> str:
        src = it.get("source_file") or ""
        if src and kb_dir.exists():
            p = kb_dir / src
            if p.exists():
                raw = p.read_text(encoding="utf-8", errors="ignore")
                return sample_text(raw, 8000)
        return it.get("core_view", "") or ""

    for it in items:
        date = it.get("date") or ""
        title = it.get("title") or ""
        source = title or it.get("source_file") or ""
        evidence = it.get("evidence_anchors") or []
        if evidence:
            for a in evidence:
                text = (a.get("text") or "").strip()
                if not text:
                    continue
                if is_bad(text):
                    continue
                if len(text) < 40 or len(text) > 260:
                    continue
                toks = tokenize(text)
                if len(toks) < 3:
                    continue
                anchors.append((date, source, text))
            continue

        doc_text = load_doc_text(it)
        for text in extract_sentences(doc_text, limit=2):
            anchors.append((date, source, text))

    # De-duplicate by text
    seen = set()
    uniq = []
    for date, source, text in anchors:
        key = re.sub(r"\s+", " ", text)
        if key in seen:
            continue
        seen.add(key)
        uniq.append((date, source, text))

    uniq.sort(key=lambda x: x[0])
    uniq = uniq[: args.limit]

    lines = []
    lines.append("# Evidence Anchors")
    lines.append("")
    lines.append(f"- 总条目数：{len(uniq)}")
    lines.append("")
    for i, (date, source, text) in enumerate(uniq, 1):
        lines.append(f"{i}. {date} | {source} | \"{text}\"")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"[done] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
