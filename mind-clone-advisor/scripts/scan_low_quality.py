#!/usr/bin/env python3
"""Scan kb/plain_text for low-quality or error pages."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from utils import setup_logging

logger = setup_logging(__name__)

BAD_PATTERNS = [
    r"404",
    r"page not found",
    r"not found",
    r"access denied",
    r"cloudflare",
    r"captcha",
    r"please enable javascript",
    r"sign in",
    r"log in",
    r"login",
    r"register",
    r"页面没有找到",
    r"页面不存在",
    r"请稍后再试",
    r"内容不存在",
    r"内容已删除",
    r"证券时报官方网站-中国资本市场信息披露平台",
    r"^404$",
    r"subscribe",
    r"not available",
    r"error",
    r"forbidden",
]


def looks_garbled(text: str) -> bool:
    # Common mojibake fragments seen in corrupted GBK/UTF-8 conversions.
    markers = ("Ã", "Â", "Ð", "Ö", "Ä", "È", "£", "¼", "¤", "ï")
    short = text[:5000]
    hits = sum(short.count(m) for m in markers)
    return hits >= 12


def match_patterns(text: str) -> list[str]:
    hits = []
    for pat in BAD_PATTERNS:
        if re.search(pat, text, re.I):
            hits.append(pat)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain-text-dir", required=True)
    parser.add_argument("--min-chars", type=int, default=400)
    parser.add_argument("--out", default="", help="optional output list path")
    args = parser.parse_args()

    plain_dir = Path(args.plain_text_dir)
    paths = sorted(plain_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"no .md files found in {plain_dir}")

    lines = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        reasons = []
        if len(text.strip()) < args.min_chars:
            reasons.append("too_short")
        hits = match_patterns(text)
        if hits:
            reasons.append("pattern:" + ",".join(hits))
        if looks_garbled(text):
            reasons.append("garbled_text")
        if reasons:
            lines.append(f"{path.name}\t{';'.join(reasons)}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    logger.info(f"[done] flagged={len(lines)}")
    for line in lines[:200]:
        logger.info(line)
    if len(lines) > 200:
        logger.info(f"... ({len(lines) - 200} more)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
