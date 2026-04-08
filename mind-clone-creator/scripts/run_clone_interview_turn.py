#!/usr/bin/env python3
"""Run one interview-state turn: advance interview state and emit a compact summary."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def resolve_turn_input(raw_input: str, input_json_path: str) -> tuple[str, dict[str, Any]]:
    if not input_json_path:
        return raw_input, {}
    payload = load_json(Path(input_json_path).resolve())
    if raw_input.strip():
        return raw_input, payload
    return str(payload.get("suggested_input", "")).strip(), payload


def resolve_user_action(raw_user_action: str, input_payload: dict[str, Any]) -> tuple[str, str]:
    if raw_user_action.strip():
        return raw_user_action.strip(), "cli"
    if input_payload:
        action = str(input_payload.get("recommended_user_action", "")).strip()
        if action in {"answer", "confirm", "accept_for_now", "accept_final", "revise", "skip"}:
            return action, "input_json"
    return "answer", "default"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one clone interview turn.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--personal-interview", required=True)
    parser.add_argument("--workflow-interview")
    parser.add_argument("--input", default="")
    parser.add_argument("--input-json", help="Optional structured NEXT_INTERVIEW_UPDATE.json payload")
    parser.add_argument(
        "--user-action",
        default="",
        choices=["answer", "confirm", "accept_for_now", "accept_final", "revise", "skip"],
        help="Semantic action for this interview turn. If omitted, can be inferred from --input-json.",
    )
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    turn_input, input_payload = resolve_turn_input(args.input, args.input_json or "")
    user_action, user_action_source = resolve_user_action(args.user_action, input_payload)

    with tempfile.TemporaryDirectory(prefix="clone-interview-turn-") as tmpdir:
        tmp = Path(tmpdir)
        next_state = tmp / "clone_interview_state.next.json"
        summary_path = tmp / "clone_interview_turn_summary.json"
        command = [
            "python3",
            str(workdir / "scripts" / "advance_clone_interview_state.py"),
            "--state",
            str(Path(args.state).resolve()),
            "--personal-interview",
            str(Path(args.personal_interview).resolve()),
            "--output-state",
            str(next_state),
            "--output-summary",
            str(summary_path),
            "--input",
            turn_input,
            "--user-action",
            user_action,
        ]
        if args.workflow_interview:
            command.extend(["--workflow-interview", str(Path(args.workflow_interview).resolve())])
        run_command(command, workdir)
        state = load_json(next_state)
        summary = load_json(summary_path)
        if input_payload:
            summary["input_payload"] = input_payload
            summary["resolved_input"] = turn_input
        summary["resolved_user_action"] = user_action
        summary["user_action_source"] = user_action_source
        (output_dir / "clone_interview_state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "clone_interview_turn_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
