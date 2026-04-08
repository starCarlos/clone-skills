#!/usr/bin/env python3
"""Build a structured queue of pending interview sections and recommended actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def infer_recommended_actions(item: dict[str, Any]) -> tuple[str, list[str]]:
    assessment = str(item.get("status", "")).strip()
    final_ready = bool(item.get("final_ready", False))
    override_status = str(item.get("override_status", "")).strip()
    strategy = item.get("follow_up_strategy", {}) if isinstance(item.get("follow_up_strategy", {}), dict) else {}
    must_answer = bool(strategy.get("must_answer_before_continue", False))

    if override_status == "accepted_for_now":
        return "accept_final", ["accept_final", "revise", "answer"]
    if override_status == "accepted_final" or final_ready:
        return "accept_final", ["accept_final", "revise"]
    if assessment == "missing":
        return "answer", ["answer", "skip"]
    if assessment == "insufficient":
        if must_answer:
            return "answer", ["answer", "revise", "skip"]
        return "answer", ["answer", "accept_for_now", "revise", "skip"]
    return "answer", ["answer", "accept_final", "revise", "skip"]


def collect_actions(state: dict[str, Any], bucket: str) -> list[dict[str, Any]]:
    return collect_actions_with_contracts(state, bucket, {})


def build_execution_contract(
    item: dict[str, Any],
    bucket: str,
    context: dict[str, str],
    current_section: str,
) -> dict[str, str]:
    section = str(item.get("section", "")).strip()
    target_file = context.get(f"{bucket}_interview", "")
    if section and section == current_section:
        return {
            "type": "run_clone_interview_turn",
            "precondition": f"先按当前 next update 补写 {section}，然后直接运行 interview turn。",
            "command": context.get("run_turn_command", ""),
            "input_source": context.get("next_update_json", ""),
            "output_artifact": context.get("run_turn_output", ""),
            "stop_condition": "读取 turn summary；若仍需补料，继续编辑后重跑；若该题已通过，则转到下一题。",
        }
    return {
        "type": "edit_then_refresh",
        "precondition": f"先在目标访谈文件里补写 {section}。",
        "command": context.get("refresh_command", ""),
        "input_source": target_file,
        "output_artifact": context.get("refresh_output", ""),
        "stop_condition": "刷新 bundle 后重新读取 pending action 队列，确认该题是否仍未 final-ready。",
    }


def classify_execution_readiness(item: dict[str, Any], current_section: str) -> tuple[str, str]:
    section = str(item.get("section", "")).strip()
    override_status = str(item.get("override_status", "")).strip()
    status = str(item.get("status", "")).strip()
    must_answer = bool(
        (item.get("must_answer_before_continue", False))
        or (
            isinstance(item.get("follow_up_strategy", {}), dict)
            and bool(item.get("follow_up_strategy", {}).get("must_answer_before_continue", False))
        )
    )
    if section and section == current_section:
        return ("current_executable_now", "当前 section 已经对齐 next update，可直接执行 interview turn。")
    if override_status == "accepted_for_now":
        return ("needs_human_confirmation", "该题曾被临时放行；若要收敛到 final，通常需要人工最终确认或补写后再推进。")
    if must_answer or status == "missing":
        return ("needs_content_edit", "需要先人工补写目标访谈文件，再刷新 bundle 或运行下一轮 turn。")
    if status == "insufficient":
        return ("needs_content_edit", "当前内容不足以 final-ready，建议先补真实细节或例子。")
    return ("needs_build_step", "当前不是直接可执行项，通常需要先刷新 bundle 或继续上游构建。")


def collect_actions_with_contracts(state: dict[str, Any], bucket: str, context: dict[str, str]) -> list[dict[str, Any]]:
    progress_key = "personal_progress" if bucket == "personal" else "workflow_progress"
    progress = state.get(progress_key, {}) if isinstance(state.get(progress_key, {}), dict) else {}
    statuses = progress.get("section_statuses", []) if isinstance(progress.get("section_statuses", []), list) else []
    current_section = str(state.get("current_section", "")).strip()
    results: list[dict[str, Any]] = []
    for item in statuses:
        if not isinstance(item, dict) or item.get("final_ready", False):
            continue
        recommended, allowed = infer_recommended_actions(item)
        strategy = item.get("follow_up_strategy", {}) if isinstance(item.get("follow_up_strategy", {}), dict) else {}
        execution_readiness, readiness_reason = classify_execution_readiness(item, current_section)
        results.append(
            {
                "scope": bucket,
                "section": str(item.get("section", "")).strip(),
                "phase": str(item.get("phase", "")).strip(),
                "status": str(item.get("status", "")).strip(),
                "override_status": str(item.get("override_status", "")).strip(),
                "reasons": [str(x) for x in item.get("reasons", []) if str(x).strip()],
                "follow_up_question": str(strategy.get("question", "")).strip(),
                "example_hint": str(strategy.get("example_hint", "")).strip(),
                "must_answer_before_continue": bool(strategy.get("must_answer_before_continue", False)),
                "recommended_user_action": recommended,
                "allowed_user_actions": allowed,
                "execution_readiness": execution_readiness,
                "execution_readiness_reason": readiness_reason,
                "manual_edit_required": execution_readiness != "current_executable_now",
                "execution_mode": "ready_to_run" if execution_readiness == "current_executable_now" else execution_readiness,
                "execution_contract": build_execution_contract(item, bucket, context, current_section),
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pending interview action queue.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--personal-interview", default="")
    parser.add_argument("--workflow-interview", default="")
    parser.add_argument("--next-update-json", default="")
    parser.add_argument("--run-turn-command", default="")
    parser.add_argument("--run-turn-output", default="")
    parser.add_argument("--refresh-command", default="")
    parser.add_argument("--refresh-output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = load_json(Path(args.state).resolve())
    context = {
        "personal_interview": args.personal_interview,
        "workflow_interview": args.workflow_interview,
        "next_update_json": args.next_update_json,
        "run_turn_command": args.run_turn_command,
        "run_turn_output": args.run_turn_output,
        "refresh_command": args.refresh_command,
        "refresh_output": args.refresh_output,
    }
    output = {
        "personal": collect_actions_with_contracts(state, "personal", context),
        "workflow": collect_actions_with_contracts(state, "workflow", context),
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
