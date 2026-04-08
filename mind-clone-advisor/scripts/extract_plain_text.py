#!/usr/bin/env python3
"""Convert full_archive files to clean plain_text.

Standardized pipeline:
1. Strip YAML front matter
2. Remove HTML tags and entities
3. Apply UNIVERSAL_WEB_NOISE + domain cleanup_patterns
4. Handle Chinese "## 正文" section markers
5. Write clean .md files to output directory

Usage:
    python3 extract_plain_text.py \
        --input-dir /path/to/kb/full_archive \
        --output-dir /path/to/kb/plain_text \
        --config /path/to/analysis/domain_config.json
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from domain_config import load_config
from utils import strip_front_matter, clean_line_noise, setup_logging

logger = setup_logging(__name__)

# HTML tag pattern
HTML_TAG_RE = re.compile(r"<[^>]+>")
# Multiple blank lines
MULTI_BLANK_RE = re.compile(r"\n{3,}")


def clean_html(text: str) -> str:
    """Remove HTML tags and decode HTML entities."""
    text = HTML_TAG_RE.sub("", text)
    text = html.unescape(text)
    return text


def extract_body_section(text: str) -> str:
    """Extract content after Chinese '## 正文' marker if present."""
    marker_patterns = [
        r"^##\s*正文\s*$",
        r"^##\s*正文内容\s*$",
        r"^##\s*文章正文\s*$",
    ]
    for pat in marker_patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            return text[m.end():].strip()
    return text


def apply_cleanup(text: str, patterns: list[str]) -> str:
    """Remove all cleanup patterns from text."""
    for pat in patterns:
        text = text.replace(pat, "")
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and trailing whitespace."""
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)
    text = MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip() + "\n"


def process_file(text: str, cleanup_patterns: list[str], line_noise_patterns: list[str] | None = None) -> str:
    """Full cleanup pipeline for a single file."""
    text = strip_front_matter(text)
    text = extract_body_section(text)
    text = clean_html(text)
    text = apply_cleanup(text, cleanup_patterns)
    if line_noise_patterns:
        text = clean_line_noise(text, line_noise_patterns)
    text = normalize_whitespace(text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert full_archive to clean plain_text."
    )
    parser.add_argument(
        "--input-dir", required=True, help="full_archive directory"
    )
    parser.add_argument(
        "--output-dir", required=True, help="plain_text output directory"
    )
    parser.add_argument(
        "--config", default=None, help="domain_config.json path"
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    cleanup_patterns = cfg["cleanup_patterns"]
    line_noise_patterns = cfg.get("line_noise_patterns", [])

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        raise SystemExit(f"input directory not found: {input_dir}")

    files = sorted(
        list(input_dir.glob("*.md"))
        + list(input_dir.glob("*.html"))
        + list(input_dir.glob("*.txt"))
    )
    if not files:
        raise SystemExit(f"no files found in {input_dir}")

    converted = 0
    skipped = 0
    for path in files:
        out_name = path.stem + ".md"
        out_path = output_dir / out_name
        if out_path.exists():
            skipped += 1
            continue

        raw = path.read_text(encoding="utf-8", errors="ignore")
        clean = process_file(raw, cleanup_patterns, line_noise_patterns)

        # Skip files that are too short after cleanup (likely noise)
        if len(clean.strip()) < 100:
            logger.warning(f"[skip] {path.name} — too short after cleanup ({len(clean.strip())} chars)")
            skipped += 1
            continue

        out_path.write_text(clean, encoding="utf-8")
        converted += 1

    logger.info(f"[done] converted={converted} skipped={skipped} out={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
