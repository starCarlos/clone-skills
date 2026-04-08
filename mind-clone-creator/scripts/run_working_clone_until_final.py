#!/usr/bin/env python3
"""Refresh a working-clone bundle until final-ready or human input is required."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from working_clone_dispatch import (
        choose_recommended_next_command,
        load_pending_actions,
        split_pending_actions,
    )
except ModuleNotFoundError:
    from scripts.working_clone_dispatch import (
        choose_recommended_next_command,
        load_pending_actions,
        split_pending_actions,
    )


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_next_update_preview(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = load_text(path)
    section = ""
    follow_up_question = ""
    example_hint = ""
    suggested_input = ""
    lines = [line.rstrip() for line in text.splitlines()]
    in_input_block = False
    input_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- section:"):
            section = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- follow_up_question:"):
            follow_up_question = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- example_hint:"):
            example_hint = stripped.split(":", 1)[1].strip()
        elif stripped == "```text":
            in_input_block = True
            input_lines = []
        elif stripped == "```" and in_input_block:
            in_input_block = False
            suggested_input = "\n".join(input_lines).strip()
        elif in_input_block:
            input_lines.append(line)
    preview_lines = lines[:24]
    return {
        "section": section,
        "follow_up_question": follow_up_question,
        "example_hint": example_hint,
        "suggested_input": suggested_input,
        "preview_markdown": "\n".join(preview_lines).strip(),
    }


def load_next_update_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    json_path = str(manifest.get("next_interview_update_json_path", "")).strip()
    if json_path and Path(json_path).exists():
        return load_json(Path(json_path))
    md_path = str(manifest.get("next_interview_update_path", "")).strip()
    if md_path:
        return extract_next_update_preview(Path(md_path))
    return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh working clone bundle until final or human input is required.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-cycles", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    manifest_path = Path(args.manifest).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cycles: list[dict[str, Any]] = []
    stop_reason = "max_cycles_reached"
    final_validation: dict[str, Any] = {}
    final_manifest: dict[str, Any] = {}

    for cycle in range(1, args.max_cycles + 1):
        refresh_cmd = [
            "python3",
            str(workdir / "scripts" / "refresh_working_clone_bundle.py"),
            "--manifest",
            str(manifest_path),
        ]
        subprocess.run(refresh_cmd, cwd=workdir, check=True)
        final_manifest = load_json(manifest_path)
        final_validation = (
            final_manifest.get("bundle_validation", {})
            if isinstance(final_manifest.get("bundle_validation", {}), dict)
            else {}
        )
        next_update = str(final_manifest.get("next_interview_update_path", "")).strip()
        cycles.append(
            {
                "cycle": cycle,
                "recommended_release": str(final_validation.get("recommended_release", "draft")),
                "final_ready": bool(final_validation.get("final_ready", False)),
                "blocker_count": len(final_validation.get("blockers", []))
                if isinstance(final_validation.get("blockers", []), list)
                else 0,
                "next_interview_update_path": next_update,
            }
        )
        if final_validation.get("final_ready", False):
            stop_reason = "final_ready"
            break
        if next_update and Path(next_update).exists():
            stop_reason = "needs_human_input"
            break

    pending_actions = load_pending_actions(final_manifest)
    pending_action_groups = split_pending_actions(pending_actions)
    summary = {
        "stop_reason": stop_reason,
        "cycle_count": len(cycles),
        "manifest": str(manifest_path),
        "bundle_validation_path": str(final_manifest.get("bundle_validation_path", "")),
        "next_interview_update_path": str(final_manifest.get("next_interview_update_path", "")),
        "next_interview_update": load_next_update_payload(final_manifest),
        "pending_interview_actions_path": str(final_manifest.get("pending_interview_actions_path", "")),
        "pending_interview_actions": pending_actions,
        "pending_interview_action_groups": pending_action_groups,
        "recommended_next_command": choose_recommended_next_command(final_manifest, final_validation, pending_action_groups),
        "final_recommended_release": str(final_validation.get("recommended_release", "draft")),
        "final_ready": bool(final_validation.get("final_ready", False)),
        "blockers": final_validation.get("blockers", []),
        "cycles": cycles,
    }
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
