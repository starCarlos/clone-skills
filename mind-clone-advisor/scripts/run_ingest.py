#!/usr/bin/env python3
"""Run a pluggable ingestor script with a standard CLI contract."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def resolve_ingestor(raw: str, base_dir: Path) -> Path:
    p = Path(raw)
    if p.exists():
        return p.resolve()

    candidates = [
        base_dir / "scripts" / raw,
        base_dir / "scripts" / f"{raw}.py",
        base_dir / "scripts" / "ingestors" / raw,
        base_dir / "scripts" / "ingestors" / f"{raw}.py",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise SystemExit(f"ingestor not found: {raw}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingestor", required=True, help="path or name of ingestor")
    parser.add_argument("--skill-dir", required=True, help="target skill directory")
    parser.add_argument("--source-config", required=True, help="source config json")
    parser.add_argument("--plain-text-dir", default="", help="override plain_text dir")
    parser.add_argument("--full-archive-dir", default="", help="override full_archive dir")
    parser.add_argument("--manifest", default="", help="override manifest path")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--since", default="", help="since date for incremental sync")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]
    ingestor = resolve_ingestor(args.ingestor, base_dir)

    skill_dir = Path(args.skill_dir)
    plain_dir = Path(args.plain_text_dir) if args.plain_text_dir else skill_dir / "kb" / "plain_text"
    full_dir = Path(args.full_archive_dir) if args.full_archive_dir else skill_dir / "kb" / "full_archive"
    # NOTE: keep ingestion manifest separate from the kb manifest built by rebuild_from_kb.py.
    # kb/manifest.jsonl is reserved for the kb manifest (file stems, language, word_count, ...).
    # This ingestion manifest persists across rebuilds and enables true incremental sync.
    manifest = Path(args.manifest) if args.manifest else skill_dir / "kb" / "manifest.ingest.jsonl"

    plain_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(ingestor),
        "--plain-text-dir",
        str(plain_dir),
        "--full-archive-dir",
        str(full_dir),
        "--manifest",
        str(manifest),
        "--source-config",
        args.source_config,
    ]
    if args.incremental:
        cmd.append("--incremental")
    if args.since:
        cmd.extend(["--since", args.since])

    subprocess.run(cmd, check=True)
    print(f"[done] ingested -> {plain_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
