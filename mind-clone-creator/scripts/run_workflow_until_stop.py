#!/usr/bin/env python3
"""Run workflow turns repeatedly until completion, human intervention, or turn limit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def run_command(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def next_input(default_mode: str, summary: dict[str, Any], turn_index: int) -> str:
    current_stage = str(summary.get("current_stage", "")).strip() or f"阶段{turn_index}"
    next_action = str(summary.get("next_action", "")).strip() or "继续推进"
    if default_mode == "complete":
        return f"{current_stage}阶段已完成，{next_action}"
    return f"继续处理：{next_action}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run workflow turns until completion, human intervention, or max turns."
    )
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--initial-input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--artifact-dir", default="workflow-runtime-artifacts")
    parser.add_argument("--profession", default="")
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--default-mode", choices=["complete", "continue"], default="complete")
    parser.add_argument("--execute-safe", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    current_state = Path(args.state).resolve()
    current_input = args.initial_input
    turns: list[dict[str, Any]] = []
    stop_reason = "max_turns_reached"

    with tempfile.TemporaryDirectory(prefix="workflow-until-stop-") as tmpdir:
        tmp_root = Path(tmpdir)

        for turn in range(1, args.max_turns + 1):
            turn_dir = output_dir / f"turn-{turn:02d}"
            turn_dir.mkdir(parents=True, exist_ok=True)

            run_cmd = [
                "python3",
                str(workdir / "scripts/run_workflow_turn.py"),
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                str(current_state),
                "--input",
                current_input,
                "--workspace",
                args.workspace,
                "--artifact-dir",
                args.artifact_dir,
                "--profession",
                args.profession,
                "--output-dir",
                str(turn_dir),
            ]
            if args.execute_safe:
                run_cmd.append("--execute-safe")
            run_command(run_cmd, workdir)

            summary = load_json(turn_dir / "workflow_turn_summary.json")
            execution = load_json(turn_dir / "workflow_execution_result.json")
            turns.append(
                {
                    "turn": turn,
                    "input": current_input,
                    "summary": summary,
                    "execution_mode": execution.get("execution_mode", ""),
                }
            )

            new_state = turn_dir / "workflow_task_state.yaml"
            current_state = new_state

            state_text = new_state.read_text(encoding="utf-8")
            state_copy = tmp_root / f"state-{turn:02d}.yaml"
            state_copy.write_text(state_text, encoding="utf-8")

            if summary.get("needs_user") is True:
                stop_reason = "needs_user"
                break

            status_line = ""
            for line in state_text.splitlines():
                if line.startswith('status: "'):
                    status_line = line
                    break
            if 'status: "completed"' in status_line:
                stop_reason = "completed"
                break

            current_input = next_input(args.default_mode, summary, turn)

    final_summary = {
        "stop_reason": stop_reason,
        "turn_count": len(turns),
        "final_state_path": str(current_state),
        "turns": turns,
    }
    (output_dir / "workflow_run_summary.json").write_text(
        json.dumps(final_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
