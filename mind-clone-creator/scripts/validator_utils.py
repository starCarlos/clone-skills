#!/usr/bin/env python3
"""Shared helpers for validator scripts."""

from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def extract_readme_command(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Recommended Next Command.*?```bash\n(.*?)\n```", text, re.S)
    return match.group(1).strip() if match else ""


def extract_bullet_field(text: str, label: str) -> str:
    match = re.search(rf"- {re.escape(label)}: (.+)", text)
    return match.group(1).strip() if match else ""


def emit_report(report: dict[str, Any], as_json: bool) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_source_artifact_entry(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        path_text = str(value.get("path", "")).strip()
        if not path_text:
            return {"path": "", "exists": False, "kind": "missing"}
        path = Path(path_text).resolve()
        entry: dict[str, Any] = {
            "path": str(path),
            "exists": path.exists(),
            "kind": "file" if path.is_file() else ("dir" if path.is_dir() else "missing"),
        }
        if path.is_file():
            entry["sha256"] = str(value.get("sha256", "")).strip() or file_sha256(path)
        return entry
    path_text = str(value).strip()
    if not path_text:
        return {"path": "", "exists": False, "kind": "missing"}
    path = Path(path_text).resolve()
    entry = {
        "path": str(path),
        "exists": path.exists(),
        "kind": "file" if path.is_file() else ("dir" if path.is_dir() else "missing"),
    }
    if path.is_file():
        entry["sha256"] = file_sha256(path)
    return entry


def normalize_source_artifacts_block(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, item in value.items():
        normalized[str(key)] = normalize_source_artifact_entry(item)
    return normalized


def validate_source_artifacts_block(
    manifest: dict[str, Any],
    required_keys: list[str],
    expected_file_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    block = normalize_source_artifacts_block(manifest.get("source_artifacts", {}))
    expected_file_map = expected_file_map or {}
    missing_keys = [key for key in required_keys if key not in block]
    non_absolute_keys = [
        key for key, entry in block.items() if entry.get("path") and not Path(str(entry.get("path", ""))).is_absolute()
    ]
    missing_existing_paths = [
        key for key, entry in block.items() if str(entry.get("path", "")).strip() and not bool(entry.get("exists", False))
    ]
    mismatched_files: list[dict[str, Any]] = []
    for key, expected_path_text in expected_file_map.items():
        entry = block.get(key, {})
        source_path_text = str(entry.get("path", "")).strip()
        if not source_path_text or not expected_path_text:
            continue
        source_path = Path(source_path_text)
        expected_path = Path(expected_path_text)
        if not source_path.exists() or not expected_path.exists() or not source_path.is_file() or not expected_path.is_file():
            continue
        source_hash = str(entry.get("sha256", "")).strip() or file_sha256(source_path)
        expected_hash = file_sha256(expected_path)
        if source_hash != expected_hash:
            mismatched_files.append(
                {
                    "key": key,
                    "source_path": str(source_path.resolve()),
                    "expected_path": str(expected_path.resolve()),
                }
            )

    ok = not missing_keys and not non_absolute_keys and not missing_existing_paths and not mismatched_files
    return {
        "present": bool(block),
        "normalized": block,
        "missing_keys": missing_keys,
        "non_absolute_keys": non_absolute_keys,
        "missing_existing_paths": missing_existing_paths,
        "mismatched_files": mismatched_files,
        "ok": ok,
    }
