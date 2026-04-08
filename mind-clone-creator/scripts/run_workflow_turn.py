#!/usr/bin/env python3
"""Run one end-to-end workflow turn: advance state -> plan actions -> execute actions."""

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
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one workflow turn by advancing state, planning actions, and executing them."
    )
    parser.add_argument("--workflow-blueprint", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--artifact-dir", default="workflow-runtime-artifacts")
    parser.add_argument("--profession", default="")
    parser.add_argument("--execute-safe", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="workflow-turn-") as tmpdir:
        tmp = Path(tmpdir)
        advanced_state = tmp / "state.next.yaml"
        step_result = tmp / "step.result.json"
        action_plan = tmp / "action.plan.json"
        execution_result = tmp / "execution.result.json"

        run_command(
            [
                "python3",
                str(workdir / "scripts/advance_workflow_task.py"),
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                args.state,
                "--input",
                args.input,
                "--output-state",
                str(advanced_state),
                "--output-result",
                str(step_result),
            ],
            workdir,
        )

        run_command(
            [
                "python3",
                str(workdir / "scripts/plan_workflow_action.py"),
                "--workflow-blueprint",
                args.workflow_blueprint,
                "--state",
                str(advanced_state),
                "--profession",
                args.profession,
                "--output",
                str(action_plan),
            ],
            workdir,
        )

        execute_cmd = [
            "python3",
            str(workdir / "scripts/execute_workflow_action.py"),
            "--action-plan",
            str(action_plan),
            "--workspace",
            args.workspace,
            "--artifact-dir",
            args.artifact_dir,
            "--profession",
            args.profession,
            "--output",
            str(execution_result),
        ]
        if args.execute_safe:
            execute_cmd.append("--execute-safe")
        run_command(execute_cmd, workdir)

        step = load_json(step_result)
        plan = load_json(action_plan)
        execution = load_json(execution_result)

        summary = {
            "current_stage": step.get("current_stage", ""),
            "next_action": step.get("next_action", ""),
            "needs_user": step.get("needs_user", False),
            "deliverable": step.get("deliverable", ""),
            "planned_tools": [item.get("tool_name", "") for item in plan.get("tool_plan", []) if isinstance(item, dict)],
            "executed_items": [
                {
                    "tool_name": item.get("tool_name", ""),
                    "status": item.get("status", ""),
                    "mode": item.get("mode", ""),
                }
                for item in execution.get("execution_items", [])
                if isinstance(item, dict)
            ],
        }

        (output_dir / "workflow_task_state.yaml").write_text(
            advanced_state.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (output_dir / "workflow_step_result.json").write_text(
            json.dumps(step, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "workflow_action_plan.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "workflow_execution_result.json").write_text(
            json.dumps(execution, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "workflow_turn_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
