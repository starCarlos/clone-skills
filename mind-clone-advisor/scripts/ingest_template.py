#!/usr/bin/env python3
"""Pluggable ingestor template.

Contract:
- Input: source_config.json (you define schema)
- Output: write normalized .md to plain_text_dir
- Optional: write raw files to full_archive_dir
- Optional: update manifest.jsonl (your schema)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_sources(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "sources" in data:
        return data["sources"]
    raise SystemExit("source-config must be a list or dict with 'sources'")


def normalize_to_markdown(text: str) -> str:
    return text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plain-text-dir", required=True)
    parser.add_argument("--full-archive-dir", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-config", required=True)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--since", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    plain_dir = Path(args.plain_text_dir)
    full_dir = Path(args.full_archive_dir)
    manifest = Path(args.manifest)
    src_cfg = Path(args.source_config)

    plain_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    sources = load_sources(src_cfg)
    print(f"[info] sources={len(sources)} incremental={args.incremental} since={args.since}")

    if args.dry_run:
        print("[info] dry-run: no files written")
        return 0

    # TODO: Implement your fetch + normalize flow here.
    # - Download or read from source
    # - Save raw files to full_archive_dir
    # - Normalize to markdown into plain_text_dir
    # - Update manifest.jsonl with metadata
    raise SystemExit("ingest_template.py is a scaffold. Implement your fetch/normalize logic.")


if __name__ == "__main__":
    raise SystemExit(main())
