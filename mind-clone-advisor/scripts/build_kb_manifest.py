#!/usr/bin/env python3
"""Build a minimal kb/manifest.jsonl from kb/plain_text."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from utils import extract_title, parse_date_from_filename, setup_logging

logger = setup_logging(__name__)

BAD_TITLE_PATTERNS = [
    r"404",
    r"not found",
    r"page not found",
    r"页面没有找到",
    r"页面不存在",
    r"证券时报官方网站-中国资本市场信息披露平台",
]


def title_is_bad(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return True
    return any(re.search(p, t, re.I) for p in BAD_TITLE_PATTERNS)


def text_is_garbled(text: str) -> bool:
    # Detect frequent mojibake markers.
    markers = ("Ã", "Â", "Ð", "Ö", "Ä", "È", "£", "¼", "¤", "ï")
    short = text[:5000]
    hits = sum(short.count(m) for m in markers)
    return hits >= 12


def word_count(text: str) -> int:
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z0-9_]+", text))
    return cn + en


def detect_language(text: str) -> str:
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z]", text))
    if cn == 0 and en == 0:
        return "unknown"
    if cn >= en:
        return "zh"
    return "en"


def write_output(path: Path, lines: list[str], overwrite: bool) -> Path:
    if path.exists() and not overwrite:
        existing = path.read_text(encoding="utf-8", errors="ignore").strip()
        if existing:
            alt = path.with_suffix(path.suffix + ".auto.jsonl")
            alt.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return alt
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain-text-dir", required=True)
    parser.add_argument("--out", required=True, help="manifest.jsonl path")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--min-word-count",
        type=int,
        default=80,
        help="skip files below this word count",
    )
    args = parser.parse_args()

    plain_dir = Path(args.plain_text_dir)
    paths = sorted(plain_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"no .md files found in {plain_dir}")

    lines = []
    skipped = 0
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = extract_title(text)
        date = parse_date_from_filename(path.name) or ""
        wc = word_count(text)
        if wc < args.min_word_count or title_is_bad(title) or text_is_garbled(text):
            skipped += 1
            continue
        obj = {
            "id": path.stem,
            "title": title,
            "date": date,
            "file": path.name,
            "language": detect_language(text),
            "word_count": wc,
        }
        lines.append(json.dumps(obj, ensure_ascii=False))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final_path = write_output(out_path, lines, overwrite=args.overwrite)
    logger.info("[done] wrote %s (kept=%d skipped=%d)", final_path, len(lines), skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
