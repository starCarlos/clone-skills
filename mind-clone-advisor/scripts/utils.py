"""Shared utilities for mind-clone-advisor scripts.

Centralizes repeated helper functions used across 20+ scripts:
text extraction, JSONL I/O, path helpers, logging, and subprocess wrappers.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the mind-clone-advisor project root (one level above scripts/)."""
    return Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(name: str) -> logging.Logger:
    """Return a logger with a simple formatter that preserves [info]/[warn]/[done] style."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ---------------------------------------------------------------------------
# Shared text constants
# ---------------------------------------------------------------------------

# Noise tokens used by cluster/theme label generators to filter stopword-like
# terms.  Shared between build_theme_clusters.py and discover_domain.py.
LABEL_NOISE: set[str] = {
    # English
    "going", "actually", "really", "don", "didn", "lot", "things",
    "put", "two", "off", "say", "com", "www", "http", "just", "get",
    "got", "way", "right", "something", "mean", "sort", "kind",
    "look", "like", "know", "think", "make", "take", "come",
    "time", "people", "world", "year", "years", "new", "one",
    "also", "well", "much", "said", "says", "told", "back",
    "down", "now", "still", "even", "per", "end", "high", "low",
    "big", "net", "pay", "news", "skip", "episode", "david",
    "dan", "charles", "bill", "watch", "cnbc", "screener",
    "podcast", "interview", "ycharts", "wealthtrack",
    # Chinese
    "我们", "他们", "这个", "那个", "这些", "那些", "这样", "那样",
    "可以", "应该", "已经", "一直", "非常", "比较", "一些", "很多",
    "什么", "怎么", "如何", "因为", "所以", "但是", "不过", "其实",
    "觉得", "认为", "知道", "时候", "问题", "事情", "开始", "后来",
}


def count_cjk(text: str) -> int:
    """Count CJK characters in *text*."""
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def count_latin(text: str) -> int:
    """Count ASCII letter characters in *text*."""
    return len(re.findall(r"[A-Za-z]", text))


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def extract_title(text: str) -> str:
    """Return the first non-empty line of *text* as the title."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def parse_date_from_filename(name: str) -> str | None:
    """Extract a date prefix like ``2024-01-15__`` from a filename."""
    m = re.match(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?__", name)
    if not m:
        return None
    date = m.group(1)
    if m.group(2):
        date += f"-{m.group(2)}"
    if m.group(3):
        date += f"-{m.group(3)}"
    return date


def split_sentences(text: str) -> list[str]:
    """Split *text* into sentences on Chinese/English punctuation, semicolons, and newlines.

    Handles both Chinese and English text:
    - Chinese: splits on 。！？!?
    - English: splits on sentence-ending punctuation followed by uppercase
    - Long clauses joined by semicolons are split further
    """
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    # Detect if predominantly Chinese
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    en_count = len(re.findall(r"[A-Za-z]", text))
    is_cn = cjk_count >= 12 and cjk_count >= en_count * 2

    if is_cn:
        parts = re.split(r"[。！？!?]+", text)
    else:
        text = text.replace("\n", " ")
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])", text)
        new_parts = []
        for p in parts:
            if ";" in p and len(p) > 200:
                new_parts.extend([x.strip() for x in p.split(";") if x.strip()])
            else:
                new_parts.append(p)
        parts = new_parts
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Split *text* on double-newlines into paragraphs."""
    parts = re.split(r"\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


def clean_line_noise(text: str, line_patterns: list[str]) -> str:
    """Remove lines that consist solely of a noise pattern (e.g. '登录', '注册').

    Unlike substring cleanup, this only strips lines where the entire trimmed
    content matches a pattern — safe for short/ambiguous words that could
    appear legitimately inside article sentences.
    """
    if not line_patterns:
        return text
    noise_set = set(line_patterns)
    lines = text.splitlines()
    cleaned = [line for line in lines if line.strip() not in noise_set]
    return "\n".join(cleaned)


def strip_front_matter(text: str) -> str:
    """Remove YAML front matter (``---`` delimited) from *text*."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


def sample_text(text: str, limit: int = 8000) -> str:
    """Return a representative sample: beginning + middle + end of *text*."""
    if len(text) <= limit:
        return text
    third = limit // 3
    mid_start = max(0, (len(text) // 2) - (third // 2))
    mid_end = min(len(text), mid_start + third)
    return text[:third] + "\n" + text[mid_start:mid_end] + "\n" + text[-third:]


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------

_jsonl_logger = setup_logging("utils.jsonl")


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, skipping blank/malformed lines with a warning."""
    items: list[dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                _jsonl_logger.warning("skipped malformed JSON at %s:%d", path.name, i)
    return items


def write_jsonl(path: Path, items: list[dict]) -> None:
    """Write a list of dicts as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Convert a display name to a URL-safe slug."""
    if not name or not name.strip():
        raise ValueError("slugify() requires a non-empty name")
    slug = name.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]+", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise ValueError(f"slugify() produced empty slug from name: {name!r}")
    return slug


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def load_registry(path: Path) -> dict:
    """Load a person registry JSON, always returning ``{"persons": [...]}``.``"""
    if not path.exists():
        return {"persons": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"persons": data}
    if isinstance(data, dict) and "persons" in data:
        return data
    raise SystemExit("registry must be a list or dict with 'persons'")


# ---------------------------------------------------------------------------
# Subprocess
# ---------------------------------------------------------------------------

def run_subprocess(cmd: list[str], dry_run: bool = False) -> None:
    """Run *cmd* via subprocess; print the command if *dry_run*."""
    if dry_run:
        print("[dry-run]", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

def validate_path_safe(base: Path, relative: str) -> Path:
    """Resolve *relative* under *base* and verify it doesn't escape *base*."""
    resolved = (base / relative).resolve()
    base_resolved = base.resolve()
    if not str(resolved).startswith(str(base_resolved)):
        raise ValueError(f"path traversal detected: {relative!r} escapes {base}")
    return resolved
