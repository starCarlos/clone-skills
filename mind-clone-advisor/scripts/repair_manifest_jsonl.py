#!/usr/bin/env python3
"""Repair recoverable manifest.jsonl corruption."""

from __future__ import annotations

import argparse
from pathlib import Path

from migration_utils import inspect_jsonl_integrity
from utils import write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair recoverable manifest.jsonl corruption")
    parser.add_argument("--manifest", required=True, help="manifest.jsonl path")
    parser.add_argument("--write", action="store_true", help="write repaired JSONL in place")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    report = inspect_jsonl_integrity(manifest_path)
    status = str(report["status"])
    entry_count = int(report["entry_count"])

    if status == "valid":
        print(f"[ok] manifest already valid: {manifest_path} (entries={entry_count})")
        return 0

    if status != "escaped_single_line":
        raise SystemExit(
            f"manifest not safely repairable: {manifest_path} status={status} entries={entry_count}"
        )

    if not args.write:
        print(f"[dry-run] recoverable manifest: {manifest_path} (entries={entry_count})")
        return 0

    write_jsonl(manifest_path, list(report["entries"]))
    print(f"[done] repaired manifest: {manifest_path} (entries={entry_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
