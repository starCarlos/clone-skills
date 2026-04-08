#!/usr/bin/env python3
"""Build a ready-to-edit next interview update note from current interview state."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def split_h3_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^###\s+(.+?)\n(.*?)(?=^###\s+|^##\s+|\Z)", re.M | re.S)
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(text)}


def load_section_template(skill_root: Path, section: str) -> str:
    if not section:
        return ""
    template_name = "workflow_interview_template.md" if section.startswith("W") else "personal_interview_template.md"
    template_path = skill_root / "templates" / template_name
    if not template_path.exists():
        return ""
    sections = split_h3_sections(template_path.read_text(encoding="utf-8"))
    return sections.get(section, "").strip()


def infer_recommended_actions(state: dict[str, Any]) -> tuple[str, list[str]]:
    assessment = str(state.get("current_assessment", "")).strip()
    final_ready = bool(state.get("current_final_ready", False))
    override_status = str(state.get("current_override_status", "")).strip()
    strategy = state.get("current_follow_up_strategy", {}) if isinstance(state.get("current_follow_up_strategy", {}), dict) else {}
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


def build_update_payload(state: dict[str, Any], section_template: str) -> dict[str, Any]:
    section = str(state.get("current_section", "")).strip() or "无"
    phase = str(state.get("current_phase", "")).strip() or "无"
    prompt = str(state.get("current_prompt", "")).strip() or "无"
    target_file = str(state.get("current_target_file", "")).strip() or "无"
    assessment = str(state.get("current_assessment", "")).strip() or "unknown"
    reasons = state.get("current_reasons", []) if isinstance(state.get("current_reasons", []), list) else []
    strategy = state.get("current_follow_up_strategy", {}) if isinstance(state.get("current_follow_up_strategy", {}), dict) else {}
    question = str(strategy.get("question", "")).strip() or "无"
    hint = str(strategy.get("example_hint", "")).strip() or "无"
    suggested_input = f"我已补充 {section}，请重新判断这一题现在是否 sufficient / final-ready；如果还不够，继续追问最关键缺口。"
    recommended_user_action, allowed_user_actions = infer_recommended_actions(state)
    return {
        "target_file": target_file,
        "phase": phase,
        "section": section,
        "assessment": assessment,
        "reasons": [str(x) for x in reasons if str(x).strip()],
        "prompt": prompt,
        "follow_up_question": question,
        "example_hint": hint,
        "section_template": section_template or "- ",
        "recommended_user_action": recommended_user_action,
        "allowed_user_actions": allowed_user_actions,
        "suggested_input": suggested_input,
    }


def render_update_note(state: dict[str, Any], section_template: str) -> str:
    payload = build_update_payload(state, section_template)
    lines = [
        "# Next Interview Update",
        "",
        f"- target_file: {payload['target_file']}",
        f"- phase: {payload['phase']}",
        f"- section: {payload['section']}",
        f"- assessment: {payload['assessment']}",
        f"- reasons: {', '.join(payload['reasons']) or '无'}",
        f"- prompt: {payload['prompt']}",
        f"- follow_up_question: {payload['follow_up_question']}",
        f"- example_hint: {payload['example_hint']}",
        f"- recommended_user_action: {payload['recommended_user_action']}",
        f"- allowed_user_actions: {', '.join(payload['allowed_user_actions'])}",
        "",
        "## Suggested Update Block",
        "",
        f"在 `{payload['section']}` 下直接补这一段，先写真实内容，再按需删改：",
        "",
        "```md",
        f"### {payload['section']}",
        payload["section_template"],
        "```",
        "",
        "## Suggested Input For run_clone_interview_turn",
        "",
        "```text",
        payload["suggested_input"],
        "```",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build next interview update note.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent
    state = load_json(Path(args.state).resolve())
    section = str(state.get("current_section", "")).strip()
    section_template = load_section_template(skill_root, section)
    payload = build_update_payload(state, section_template)
    output_md_path = Path(args.output_md).resolve()
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(render_update_note(state, section_template), encoding="utf-8")
    if args.output_json:
        output_json_path = Path(args.output_json).resolve()
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
