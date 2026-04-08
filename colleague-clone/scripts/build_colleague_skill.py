from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import build_runtime_contract, build_runtime_portraits, load_json, utc_now_iso, write_json, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a draft colleague skill from analysis outputs.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to render.")
    return parser.parse_args()


def format_confidence(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return "unknown"


def strip_leading_h1(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        if lines and lines[0] == "":
            lines = lines[1:]
    return "\n".join(lines).strip()


def render_persona(profile: dict) -> str:
    stable = profile.get("stable_patterns", [])
    semantic = profile.get("semantic_view", {})
    communication = semantic.get("communication_style", {})
    collaboration = semantic.get("collaboration_style", {})
    boundaries = semantic.get("boundary_constraints", {})
    temperament = semantic.get("temperament_profile", {})
    family_boundary = semantic.get("family_boundary_profile", {})
    overrides = profile.get("manual_overrides", [])

    lines = [
        "# Communication And Boundaries",
        "",
        "## Temperament Profile",
        f"- Summary: {temperament.get('summary', 'No temperament summary available.')}",
        f"- Tendencies: {', '.join(temperament.get('tendency_tags', [])) or 'unknown'}",
        f"- Pressure mode: {', '.join(temperament.get('pressure_mode', [])) or 'unknown'}",
        "",
        "## Communication Style",
        f"- Summary: {communication.get('summary', 'No communication summary available.')}",
        f"- Questioning tendency: {communication.get('questioning_tendency', 'unknown')}",
        f"- Disagreement style: {communication.get('disagreement_style', 'unknown')}",
        "",
        "## Collaboration Style",
        f"- Summary: {collaboration.get('summary', 'No collaboration summary available.')}",
        f"- Coordination mode: {collaboration.get('coordination_mode', 'unknown')}",
        "",
        "## Boundary Constraints",
        f"- Summary: {boundaries.get('summary', 'No boundary summary available.')}",
        f"- Stress response: {', '.join(boundaries.get('stress_response_modes', [])) or 'unknown'}",
        "",
        "## Family Boundary",
        f"- Summary: {family_boundary.get('summary', 'No family-boundary summary available.')}",
        f"- Policy: {family_boundary.get('policy', 'unknown')}",
        f"- Allowed scope: {', '.join(family_boundary.get('allowed_scope', [])) or 'unknown'}",
        "",
        "## Observable Patterns",
    ]
    for item in stable:
        lines.append(f"- {item.get('label', 'pattern')}: {item.get('summary', '')}")
    lines.extend(["", "## Manual Overrides"])
    if overrides:
        for item in overrides:
            lines.append(
                f"- {item.get('field_path', 'unknown')}: {item.get('new_value', '')} ({item.get('reason', 'manual override')})"
            )
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def render_work(profile: dict) -> str:
    semantic = profile.get("semantic_view", {})
    scope = semantic.get("role_scope", {})
    work_method = semantic.get("work_method", {})
    review_delivery = semantic.get("review_and_delivery", {})
    professional = semantic.get("professional_profile", {})
    rules = profile.get("explicit_rules", [])
    terms = profile.get("domain_knowledge", [])
    overrides = profile.get("manual_overrides", [])

    lines = [
        "# Role And Work Method",
        "",
        "## Professional Profile",
        f"- Summary: {professional.get('summary', 'No professional profile available.')}",
        f"- Scope modules: {', '.join(professional.get('scope_modules', [])) or 'n/a'}",
        f"- Operating sequence: {', '.join(professional.get('operating_sequence', [])) or 'n/a'}",
        f"- Review focus: {', '.join(professional.get('review_focus_areas', [])) or 'n/a'}",
        "",
        "## Role Scope",
        f"- Summary: {scope.get('summary', 'No scope summary available.')}",
        f"- Modules: {', '.join(scope.get('modules', [])) or 'n/a'}",
        "",
        "## Work Method",
        f"- Summary: {work_method.get('summary', 'No work-method summary available.')}",
        f"- Sequence: {', '.join(work_method.get('operating_sequence', [])) or 'n/a'}",
        "",
        "## Review And Delivery",
        f"- Summary: {review_delivery.get('summary', 'No review/delivery summary available.')}",
        f"- Focus areas: {', '.join(review_delivery.get('focus_areas', [])) or 'n/a'}",
        f"- Formats: {', '.join(review_delivery.get('format_preferences', [])) or 'n/a'}",
        "",
        "## Explicit Rules",
    ]
    if rules:
        for item in rules:
            lines.append(f"- {item.get('summary', '')}")
    else:
        lines.append("- No explicit rules extracted yet.")
    lines.extend(
        [
            "",
            "## Domain Knowledge",
            f"- Terms: {', '.join(terms) if terms else 'n/a'}",
            "",
            "## Manual Overrides",
        ]
    )
    if overrides:
        for item in overrides:
            lines.append(
                f"- {item.get('field_path', 'unknown')}: {item.get('new_value', '')} ({item.get('reason', 'manual override')})"
            )
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def render_runtime_portraits(runtime_portraits: dict) -> str:
    professional = runtime_portraits.get("professional_portrait", {})
    temperament = runtime_portraits.get("temperament_portrait", {})
    family_boundary = runtime_portraits.get("family_boundary_portrait", {})
    answer_strategy = runtime_portraits.get("answer_strategy", {})

    lines = [
        "## Runtime Portraits",
        "",
        "### Professional Portrait",
        f"- Summary: {professional.get('summary', 'No professional profile available.')}",
        f"- Scope modules: {', '.join(professional.get('scope_modules', [])) or 'n/a'}",
        f"- Operating sequence: {', '.join(professional.get('operating_sequence', [])) or 'n/a'}",
        f"- Review focus: {', '.join(professional.get('review_focus_areas', [])) or 'n/a'}",
        f"- Confidence: {format_confidence(professional.get('confidence'))}",
        "",
        "### Temperament Portrait",
        f"- Summary: {temperament.get('summary', 'No temperament summary available.')}",
        f"- Tendencies: {', '.join(temperament.get('tendency_tags', [])) or 'unknown'}",
        f"- Pressure mode: {', '.join(temperament.get('pressure_mode', [])) or 'unknown'}",
        f"- Confidence: {format_confidence(temperament.get('confidence'))}",
        "",
        "### Family Boundary Portrait",
        f"- Summary: {family_boundary.get('summary', 'No family-boundary summary available.')}",
        f"- Policy: {family_boundary.get('policy', 'unknown')}",
        f"- Allowed scope: {', '.join(family_boundary.get('allowed_scope', [])) or 'unknown'}",
        f"- Redirect topics: {', '.join(family_boundary.get('redirect_topics', [])) or 'unknown'}",
        f"- Confidence: {format_confidence(family_boundary.get('confidence'))}",
        "",
        "### Runtime Answer Strategy",
        f"- Default modules: {', '.join(answer_strategy.get('default_modules', [])) or 'n/a'}",
        f"- Default review focus: {', '.join(answer_strategy.get('default_review_focus', [])) or 'n/a'}",
        f"- Workflow sequence: {', '.join(answer_strategy.get('workflow_sequence', [])) or 'n/a'}",
        f"- Interaction tendencies: {', '.join(answer_strategy.get('interaction_tendencies', [])) or 'unknown'}",
        f"- Delivery preferences: {', '.join(answer_strategy.get('delivery_preferences', [])) or 'n/a'}",
        f"- Boundary policy: {answer_strategy.get('boundary_policy', 'unknown')}",
    ]
    return "\n".join(lines) + "\n"


def build_evidence_index(persona_profile: dict, work_profile: dict) -> list[dict]:
    items: list[dict] = []
    for field_path, evidence_list in [
        ("persona.expression_style", persona_profile.get("expression_style", {}).get("evidence", [])),
        ("persona.decision_patterns", persona_profile.get("decision_patterns", {}).get("evidence", [])),
        ("persona.collaboration_style", persona_profile.get("collaboration_style", {}).get("evidence", [])),
        ("persona.stress_behaviors", persona_profile.get("stress_behaviors", {}).get("evidence", [])),
        ("persona.boundaries_and_taboos", persona_profile.get("boundaries_and_taboos", {}).get("evidence", [])),
        ("work.responsibility_scope", work_profile.get("responsibility_scope", {}).get("evidence", [])),
        ("work.workflow_patterns", work_profile.get("workflow_patterns", {}).get("evidence", [])),
        ("work.review_preferences", work_profile.get("review_preferences", {}).get("evidence", [])),
        ("work.delivery_preferences", work_profile.get("delivery_preferences", {}).get("evidence", [])),
    ]:
        for index, evidence in enumerate(evidence_list, start=1):
            items.append(
                {
                    "evidence_id": f"{field_path.replace('.', '_')}_{index:03d}",
                    "field_path": field_path,
                    **evidence,
                }
            )
    for index, rule in enumerate(work_profile.get("explicit_rules", []), start=1):
        for evidence in rule.get("evidence", []):
            items.append(
                {
                    "evidence_id": f"work_explicit_rules_{index:03d}",
                    "field_path": "work.explicit_rules",
                    **evidence,
                }
            )
    return items


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    meta_path = bundle_dir / "meta.json"
    meta = load_json(meta_path)
    persona_profile = load_json(bundle_dir / "analysis" / "persona_profile.json")
    work_profile = load_json(bundle_dir / "analysis" / "work_profile.json")

    persona_md = render_persona(persona_profile)
    work_md = render_work(work_profile)
    evidence_index = build_evidence_index(persona_profile, work_profile)
    runtime_contract = build_runtime_contract(persona_profile, work_profile)
    runtime_portraits = build_runtime_portraits(persona_profile, work_profile, runtime_contract)
    runtime_portraits_md = render_runtime_portraits(runtime_portraits)

    (bundle_dir / "persona.md").write_text(persona_md, encoding="utf-8")
    (bundle_dir / "work.md").write_text(work_md, encoding="utf-8")
    write_json(bundle_dir / "analysis" / "runtime_contract.json", runtime_contract)
    write_json(bundle_dir / "analysis" / "runtime_portraits.json", runtime_portraits)
    (bundle_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f'name: colleague-{meta["slug"]}',
                f'description: Draft colleague clone for {meta["name"]}',
                "user-invocable: true",
                "---",
                "",
                f"# {meta['name']}",
                "",
                "This is a draft colleague clone built from private work materials.",
                "",
                runtime_portraits_md.strip(),
                "",
                "## Role And Work Method",
                "",
                strip_leading_h1(work_md),
                "",
                "## Communication And Boundaries",
                "",
                strip_leading_h1(persona_md),
                "",
                "## Runtime Rules",
                "",
                *[f"{index}. {rule}" for index, rule in enumerate(runtime_contract["runtime_rules"], start=1)],
                "",
                "## Runtime Boundaries",
                "",
                *[f"- {rule}" for rule in runtime_contract["runtime_boundaries"]],
                "",
                "## Known Unknowns",
                "",
                *[f"- {item}" for item in runtime_contract["known_unknowns"]["rendered"]],
                "",
                "## Refusal Pattern",
                "",
                f'- Say: "{runtime_contract["refusal_pattern"]["say"]}"',
                f'- Then redirect to {", ".join(runtime_contract["refusal_pattern"]["redirect_to"])}.',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_jsonl(bundle_dir / "evidence_index.jsonl", evidence_index)

    meta["state"] = "draft_generated"
    meta["updated_at"] = utc_now_iso()
    meta["rendered_files"] = {
        "persona_md": str(bundle_dir / "persona.md"),
        "work_md": str(bundle_dir / "work.md"),
        "skill_md": str(bundle_dir / "SKILL.md"),
        "runtime_contract_json": str(bundle_dir / "analysis" / "runtime_contract.json"),
        "runtime_portraits_json": str(bundle_dir / "analysis" / "runtime_portraits.json"),
    }
    write_json(meta_path, meta)
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "state": meta["state"],
                "evidence_count": len(evidence_index),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
