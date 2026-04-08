from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_release_health_summary,
    build_release_manifest,
    build_release_compare_report,
    build_runtime_package,
    build_runtime_release_health_artifact,
    build_runtime_release_health_compare_report,
    build_runtime_smoke_artifact,
    build_runtime_smoke_compare_report,
    build_runtime_prompt_eval_artifact,
    build_runtime_prompt_eval_compare_report,
    build_runtime_prompt_eval_report,
    build_runtime_smoke_report,
    build_runtime_contract,
    build_runtime_portraits,
    load_json,
    load_jsonl,
    load_previous_runtime_release_health,
    load_previous_runtime_smoke,
    load_previous_runtime_prompt_eval,
    load_runtime_prompt_eval_cases,
    load_previous_release_manifest,
    runtime_prompt_eval_brief,
    runtime_release_decision,
    runtime_smoke_brief,
    normalize_runtime_release_review,
    summarize_runtime_portraits,
    runtime_portraits_review_brief,
    runtime_release_review_brief,
    runtime_release_review_issues,
    summarize_runtime_contract,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a draft colleague-clone bundle.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to validate.")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--require-final", action="store_true", help="Validate against final-readiness gates.")
    parser.add_argument("--run-runtime-smoke", action="store_true", help="Run runtime smoke checks against runtime_package.json.")
    parser.add_argument("--run-prompt-eval", action="store_true", help="Run deterministic prompt eval previews against runtime_package.json.")
    parser.add_argument("--prompt-eval-cases-file", help="Optional JSON file that defines a custom prompt eval case set.")
    parser.add_argument("--prompt-eval-mode", choices=["deterministic", "model"], default="deterministic")
    parser.add_argument("--prompt-eval-model-command", help="Executable that reads a prompt-eval JSON payload on stdin and returns {'answer': ...}.")
    return parser.parse_args()


FINAL_MARKERS = [
    "No persona summary available.",
    "No work summary available.",
    "No communication summary available.",
    "No temperament summary available.",
    "No family-boundary summary available.",
    "No professional profile available.",
    "No work-method summary available.",
    "No review/delivery summary available.",
    "No scope summary available.",
    "No workflow summary available.",
    "No review summary available.",
    "No explicit rules extracted yet.",
    "limited persona evidence",
    "limited work evidence",
    "n/a",
]


RUNTIME_CONTRACT_SECTIONS = [
    "## Runtime Rules",
    "## Runtime Boundaries",
    "## Known Unknowns",
    "## Refusal Pattern",
]


RUNTIME_PORTRAIT_SECTIONS = [
    "## Runtime Portraits",
    "### Professional Portrait",
    "### Temperament Portrait",
    "### Family Boundary Portrait",
    "### Runtime Answer Strategy",
]


def has_final_placeholders(bundle_dir: Path) -> list[str]:
    placeholders: list[str] = []
    for relative in ["persona.md", "work.md", "SKILL.md"]:
        path = bundle_dir / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FINAL_MARKERS:
            if marker in text:
                placeholders.append(f"{relative}: {marker}")
    return placeholders


def summarize_evidence_balance(evidence_items: list[dict]) -> dict:
    balance = {"persona": 0, "work": 0}
    field_coverage = {"persona": [], "work": []}
    for item in evidence_items:
        field_path = str(item.get("field_path", ""))
        if field_path.startswith("persona."):
            balance["persona"] += 1
            field_coverage["persona"].append(field_path)
        elif field_path.startswith("work."):
            balance["work"] += 1
            field_coverage["work"].append(field_path)
    return {
        "counts": balance,
        "field_coverage": {key: sorted(set(value)) for key, value in field_coverage.items()},
    }


def summarize_analysis_quality(bundle_dir: Path) -> dict:
    profiles = {
        "persona": load_json(bundle_dir / "analysis" / "persona_profile.json") if (bundle_dir / "analysis" / "persona_profile.json").exists() else {},
        "work": load_json(bundle_dir / "analysis" / "work_profile.json") if (bundle_dir / "analysis" / "work_profile.json").exists() else {},
    }
    low_confidence_fields: list[dict] = []
    analysis_conflicts: list[dict] = []
    resolved_conflicts: list[dict] = []
    resolution_history: list[dict] = []
    privacy_counts = {"work_related": 0, "work_adjacent": 0, "private_sensitive": 0}
    field_groups = {
        "persona": [
            "expression_style",
            "decision_patterns",
            "collaboration_style",
            "stress_behaviors",
            "boundaries_and_taboos",
        ],
        "work": [
            "responsibility_scope",
            "workflow_patterns",
            "review_preferences",
            "delivery_preferences",
        ],
    }
    for scope, fields in field_groups.items():
        profile = profiles.get(scope, {})
        for field_name in fields:
            field = profile.get(field_name, {})
            confidence = field.get("confidence")
            if isinstance(confidence, (int, float)) and confidence < 0.6:
                low_confidence_fields.append(
                    {
                        "field_path": f"{scope}.{field_name}",
                        "confidence": confidence,
                        "reason": field.get("confidence_reason", ""),
                    }
                )
        for item in profile.get("conflicts", []):
            analysis_conflicts.append({"scope": scope, **item})
        for item in profile.get("resolved_conflicts", []):
            resolved_conflicts.append({"scope": scope, **item})
        for item in profile.get("resolution_history", []):
            resolution_history.append({"scope": scope, **item})
        audit_counts = profile.get("privacy_filter", {}).get("counts", {})
        for key in privacy_counts:
            privacy_counts[key] = max(privacy_counts[key], int(audit_counts.get(key, 0) or 0))
    return {
        "low_confidence_fields": low_confidence_fields,
        "analysis_conflicts": analysis_conflicts,
        "resolved_conflicts": resolved_conflicts,
        "resolution_history": resolution_history,
        "privacy_counts": privacy_counts,
    }


def inspect_runtime_contract(skill_text: str, runtime_contract: dict) -> list[str]:
    issues: list[str] = []
    for heading in RUNTIME_CONTRACT_SECTIONS:
        if heading not in skill_text:
            issues.append(f"runtime contract is missing section: {heading}")

    runtime_required_caveats = runtime_contract.get("known_unknowns", {}).get("required_items", [])
    runtime_minor_caveats = runtime_contract.get("known_unknowns", {}).get("minor_items", [])
    rendered_known_unknowns = runtime_contract.get("known_unknowns", {}).get("rendered", [])
    fallback_summary = runtime_contract.get("known_unknowns", {}).get("fallback_summary", "")

    if runtime_required_caveats:
        for summary in rendered_known_unknowns:
            if summary and summary not in skill_text:
                issues.append(f"runtime contract is missing required caveat summary: {summary}")
    elif fallback_summary and fallback_summary not in skill_text:
        issues.append("runtime contract is missing the no-major-issues fallback")

    if any(item.get("kind") == "privacy_limited_area" for item in runtime_required_caveats) and "Privacy note:" not in skill_text:
        issues.append("runtime contract is missing privacy note")
    if any(item.get("kind") == "privacy_limited_area" for item in runtime_required_caveats) and "Privacy-limited area:" not in skill_text:
        issues.append("runtime contract is missing privacy-limited caveat")
    for item in runtime_minor_caveats:
        summary = item.get("summary", "")
        if summary and summary in skill_text:
            issues.append(f"runtime contract should omit minor sparse caveat: {item.get('field_path', '')}")
    refusal_say = runtime_contract.get("refusal_pattern", {}).get("say", "")
    if refusal_say and refusal_say not in skill_text:
        issues.append("runtime contract is missing refusal pattern say text")

    return issues


def inspect_portrait_semantic_views(persona_profile: dict, work_profile: dict) -> list[str]:
    issues: list[str] = []
    portrait_specs = [
        (
            "persona.semantic_view.temperament_profile",
            persona_profile.get("semantic_view", {}).get("temperament_profile", {}),
            {
                "summary": str,
                "tendency_tags": list,
                "pressure_mode": list,
                "confidence": (int, float),
                "confidence_reason": str,
                "evidence": list,
            },
        ),
        (
            "persona.semantic_view.family_boundary_profile",
            persona_profile.get("semantic_view", {}).get("family_boundary_profile", {}),
            {
                "summary": str,
                "policy": str,
                "private_signal_present": bool,
                "allowed_scope": list,
                "confidence": (int, float),
                "confidence_reason": str,
                "evidence": list,
            },
        ),
        (
            "work.semantic_view.professional_profile",
            work_profile.get("semantic_view", {}).get("professional_profile", {}),
            {
                "summary": str,
                "scope_modules": list,
                "operating_sequence": list,
                "review_focus_areas": list,
                "confidence": (int, float),
                "confidence_reason": str,
                "evidence": list,
            },
        ),
    ]

    for path, portrait, required_fields in portrait_specs:
        if not isinstance(portrait, dict) or not portrait:
            issues.append(f"missing portrait semantic view: {path}")
            continue
        summary_text = str(portrait.get("summary", "")).strip()
        summary_is_placeholder = summary_text.startswith("No stable ") or summary_text.startswith("No ")
        for field_name, expected_type in required_fields.items():
            value = portrait.get(field_name)
            if value is None:
                issues.append(f"portrait semantic view is missing field: {path}.{field_name}")
                continue
            if not isinstance(value, expected_type):
                issues.append(f"portrait semantic view has invalid type: {path}.{field_name}")
                continue
            if isinstance(value, str) and not value.strip():
                issues.append(f"portrait semantic view has empty text: {path}.{field_name}")
            if isinstance(value, list) and field_name == "allowed_scope" and not value:
                issues.append(f"portrait semantic view has empty list: {path}.{field_name}")
            if (
                isinstance(value, list)
                and field_name == "evidence"
                and path != "persona.semantic_view.family_boundary_profile"
                and not value
                and not summary_is_placeholder
            ):
                issues.append(f"portrait semantic view has empty list: {path}.{field_name}")
        confidence = portrait.get("confidence")
        if isinstance(confidence, (int, float)) and not 0 <= float(confidence) <= 1:
            issues.append(f"portrait semantic view confidence is out of range: {path}.confidence")

    family_boundary = persona_profile.get("semantic_view", {}).get("family_boundary_profile", {})
    if family_boundary.get("policy") != "refuse_and_redirect":
        issues.append("portrait semantic view has unexpected family boundary policy")
    if "role scope" not in family_boundary.get("allowed_scope", []):
        issues.append("portrait semantic view family boundary must redirect to role scope")

    return issues


def inspect_runtime_portrait_json(runtime_portraits: dict, persona_profile: dict, work_profile: dict, runtime_contract: dict) -> list[str]:
    issues: list[str] = []
    expected = build_runtime_portraits(persona_profile, work_profile, runtime_contract)
    if not isinstance(runtime_portraits, dict) or not runtime_portraits:
        return ["runtime portraits JSON is missing or invalid"]

    for field_name in [
        "contract_scope",
        "professional_portrait",
        "temperament_portrait",
        "family_boundary_portrait",
        "answer_strategy",
    ]:
        if field_name not in runtime_portraits:
            issues.append(f"runtime portraits JSON is missing field: {field_name}")

    for field_name in [
        "professional_portrait",
        "temperament_portrait",
        "family_boundary_portrait",
        "answer_strategy",
    ]:
        if field_name in runtime_portraits and runtime_portraits.get(field_name) != expected.get(field_name):
            issues.append(f"runtime portraits JSON drifted from analysis: {field_name}")

    if runtime_portraits.get("contract_scope") != expected.get("contract_scope"):
        issues.append("runtime portraits JSON drifted from analysis: contract_scope")

    return issues


def inspect_runtime_portraits(skill_text: str, runtime_portraits: dict) -> list[str]:
    issues: list[str] = []
    for heading in RUNTIME_PORTRAIT_SECTIONS:
        if heading not in skill_text:
            issues.append(f"runtime portraits are missing section: {heading}")

    portrait_expectations = [
        (
            "professional portrait summary",
            runtime_portraits.get("professional_portrait", {}).get("summary", ""),
        ),
        (
            "temperament portrait summary",
            runtime_portraits.get("temperament_portrait", {}).get("summary", ""),
        ),
        (
            "family boundary portrait summary",
            runtime_portraits.get("family_boundary_portrait", {}).get("summary", ""),
        ),
        (
            "family boundary portrait policy",
            runtime_portraits.get("family_boundary_portrait", {}).get("policy", ""),
        ),
        (
            "runtime answer boundary policy",
            runtime_portraits.get("answer_strategy", {}).get("boundary_policy", ""),
        ),
    ]
    for label, expected_text in portrait_expectations:
        if expected_text and expected_text not in skill_text:
            issues.append(f"runtime portraits are missing {label}")

    for topic in runtime_portraits.get("family_boundary_portrait", {}).get("allowed_scope", []):
        if topic and topic not in skill_text:
            issues.append(f"runtime portraits are missing allowed scope topic: {topic}")
    for topic in runtime_portraits.get("family_boundary_portrait", {}).get("redirect_topics", []):
        if topic and topic not in skill_text:
            issues.append(f"runtime portraits are missing redirect topic: {topic}")
    for item in runtime_portraits.get("answer_strategy", {}).get("default_review_focus", []):
        if item and item not in skill_text:
            issues.append(f"runtime portraits are missing default review focus: {item}")

    return issues


def inspect_release_manifest(bundle_dir: Path, release_manifest: dict, meta: dict, report: dict) -> list[str]:
    issues: list[str] = []
    expected = build_release_manifest(bundle_dir, meta, report)
    if not isinstance(release_manifest, dict) or not release_manifest:
        return ["release manifest is missing or invalid"]

    required_fields = [
        "schema_version",
        "generated_at",
        "bundle",
        "release",
        "sources",
        "evidence",
        "runtime_contract_summary",
        "runtime_portraits_summary",
        "runtime_release_review",
        "runtime_release_review_brief",
        "runtime_portraits_review_brief",
        "runtime_release_decision",
        "release_health",
        "runtime_smoke_summary",
        "runtime_prompt_eval_summary",
    ]
    for field_name in required_fields:
        if field_name not in release_manifest:
            issues.append(f"release manifest is missing field: {field_name}")
    if issues:
        return issues

    for field_name in required_fields:
        if release_manifest.get(field_name) != expected.get(field_name):
            issues.append(f"release manifest drifted from bundle: {field_name}")
    return issues


def inspect_runtime_package(bundle_dir: Path, runtime_package: dict, meta: dict, report: dict, release_manifest: dict) -> list[str]:
    issues: list[str] = []
    expected = build_runtime_package(
        bundle_dir,
        meta,
        report,
        release_manifest=release_manifest,
        release_manifest_path=str(bundle_dir / "release_manifest.json"),
    )
    if not isinstance(runtime_package, dict) or not runtime_package:
        return ["runtime package is missing or invalid"]

    required_fields = [
        "schema_version",
        "generated_at",
        "bundle",
        "system_prompt",
        "runtime_contract_summary",
        "runtime_portraits_summary",
        "release_health",
        "runtime_smoke_summary",
        "runtime_prompt_eval_summary",
        "release",
        "provenance",
    ]
    for field_name in required_fields:
        if field_name not in runtime_package:
            issues.append(f"runtime package is missing field: {field_name}")
    if issues:
        return issues

    for field_name in required_fields:
        if runtime_package.get(field_name) != expected.get(field_name):
            issues.append(f"runtime package drifted from bundle: {field_name}")
    return issues


def inspect_runtime_prompt_eval_artifact(runtime_prompt_eval_artifact: dict, expected: dict) -> list[str]:
    issues: list[str] = []
    if not isinstance(runtime_prompt_eval_artifact, dict) or not runtime_prompt_eval_artifact:
        return ["runtime prompt eval artifact is missing or invalid"]

    required_fields = [
        "schema_version",
        "generated_at",
        "runtime_package_path",
        "runtime_prompt_eval_report",
        "runtime_prompt_eval_brief",
        "runtime_prompt_eval_compare_report",
        "runtime_prompt_eval_compare_brief",
    ]
    for field_name in required_fields:
        if field_name not in runtime_prompt_eval_artifact:
            issues.append(f"runtime prompt eval artifact is missing field: {field_name}")
    if issues:
        return issues

    for field_name in required_fields:
        if runtime_prompt_eval_artifact.get(field_name) != expected.get(field_name):
            issues.append(f"runtime prompt eval artifact drifted from bundle: {field_name}")
    return issues


def inspect_runtime_smoke_artifact(runtime_smoke_artifact: dict, expected: dict) -> list[str]:
    issues: list[str] = []
    if not isinstance(runtime_smoke_artifact, dict) or not runtime_smoke_artifact:
        return ["runtime smoke artifact is missing or invalid"]

    required_fields = [
        "schema_version",
        "generated_at",
        "runtime_package_path",
        "runtime_smoke_report",
        "runtime_smoke_brief",
        "runtime_smoke_compare_report",
        "runtime_smoke_compare_brief",
    ]
    for field_name in required_fields:
        if field_name not in runtime_smoke_artifact:
            issues.append(f"runtime smoke artifact is missing field: {field_name}")
    if issues:
        return issues

    for field_name in required_fields:
        if runtime_smoke_artifact.get(field_name) != expected.get(field_name):
            issues.append(f"runtime smoke artifact drifted from bundle: {field_name}")
    return issues


def inspect_runtime_release_health_artifact(runtime_release_health_artifact: dict, expected: dict) -> list[str]:
    issues: list[str] = []
    if not isinstance(runtime_release_health_artifact, dict) or not runtime_release_health_artifact:
        return ["runtime release health artifact is missing or invalid"]

    required_fields = [
        "schema_version",
        "generated_at",
        "release_manifest_path",
        "runtime_package_path",
        "runtime_smoke_path",
        "runtime_prompt_eval_path",
        "release_health",
        "runtime_release_health_compare_report",
        "runtime_release_health_compare_brief",
    ]
    for field_name in required_fields:
        if field_name not in runtime_release_health_artifact:
            issues.append(f"runtime release health artifact is missing field: {field_name}")
    if issues:
        return issues

    for field_name in required_fields:
        if runtime_release_health_artifact.get(field_name) != expected.get(field_name):
            issues.append(f"runtime release health artifact drifted from bundle: {field_name}")
    return issues


def build_report(
    bundle_dir: Path,
    *,
    require_final: bool = False,
    check_release_manifest: bool = True,
    check_runtime_package: bool = True,
    check_runtime_smoke: bool = True,
    check_runtime_prompt_eval: bool = True,
    run_runtime_smoke: bool = False,
    run_prompt_eval: bool = False,
    prompt_eval_cases_file: str = "",
    prompt_eval_mode: str = "deterministic",
    prompt_eval_model_command: str = "",
) -> dict:
    meta = load_json(bundle_dir / "meta.json") if (bundle_dir / "meta.json").exists() else {}
    required_files = [
        bundle_dir / "meta.json",
        bundle_dir / "analysis" / "persona_profile.json",
        bundle_dir / "analysis" / "work_profile.json",
        bundle_dir / "analysis" / "runtime_contract.json",
        bundle_dir / "analysis" / "runtime_portraits.json",
        bundle_dir / "persona.md",
        bundle_dir / "work.md",
        bundle_dir / "SKILL.md",
        bundle_dir / "evidence_index.jsonl",
    ]
    release_manifest_path = bundle_dir / "release_manifest.json"
    runtime_package_path = bundle_dir / "runtime_package.json"
    runtime_smoke_path = bundle_dir / "runtime_smoke.json"
    runtime_release_health_path = bundle_dir / "runtime_release_health.json"
    runtime_prompt_eval_path = bundle_dir / "runtime_prompt_eval.json"
    if check_release_manifest and (require_final or meta.get("state") == "final_confirmed" or release_manifest_path.exists()):
        required_files.append(release_manifest_path)
    if check_runtime_package and (require_final or meta.get("state") == "final_confirmed" or runtime_package_path.exists()):
        required_files.append(runtime_package_path)
    if check_runtime_smoke and (require_final or meta.get("state") == "final_confirmed" or runtime_smoke_path.exists()):
        required_files.append(runtime_smoke_path)
    if check_runtime_package and (require_final or meta.get("state") == "final_confirmed" or runtime_release_health_path.exists()):
        required_files.append(runtime_release_health_path)
    if check_runtime_prompt_eval and (require_final or meta.get("state") == "final_confirmed" or runtime_prompt_eval_path.exists()):
        required_files.append(runtime_prompt_eval_path)
    missing = [str(path) for path in required_files if not path.exists()]
    evidence_items = load_jsonl(bundle_dir / "evidence_index.jsonl") if (bundle_dir / "evidence_index.jsonl").exists() else []
    placeholders = has_final_placeholders(bundle_dir) if require_final else []
    evidence_summary = summarize_evidence_balance(evidence_items)
    evidence_balance = evidence_summary["counts"]
    field_coverage = evidence_summary["field_coverage"]
    analysis_quality = summarize_analysis_quality(bundle_dir)
    persona_profile = load_json(bundle_dir / "analysis" / "persona_profile.json") if (bundle_dir / "analysis" / "persona_profile.json").exists() else {}
    work_profile = load_json(bundle_dir / "analysis" / "work_profile.json") if (bundle_dir / "analysis" / "work_profile.json").exists() else {}
    runtime_contract = (
        load_json(bundle_dir / "analysis" / "runtime_contract.json")
        if (bundle_dir / "analysis" / "runtime_contract.json").exists()
        else build_runtime_contract(persona_profile, work_profile)
    )
    runtime_portraits = (
        load_json(bundle_dir / "analysis" / "runtime_portraits.json")
        if (bundle_dir / "analysis" / "runtime_portraits.json").exists()
        else build_runtime_portraits(persona_profile, work_profile, runtime_contract)
    )
    skill_text = (bundle_dir / "SKILL.md").read_text(encoding="utf-8") if (bundle_dir / "SKILL.md").exists() else ""
    runtime_contract_issues = inspect_runtime_contract(skill_text, runtime_contract) if skill_text else []
    portrait_semantic_issues = inspect_portrait_semantic_views(persona_profile, work_profile)
    runtime_portrait_json_issues = (
        inspect_runtime_portrait_json(runtime_portraits, persona_profile, work_profile, runtime_contract)
        if not portrait_semantic_issues
        else []
    )
    runtime_portrait_issues = (
        inspect_runtime_portraits(skill_text, runtime_portraits)
        if skill_text and not portrait_semantic_issues and not runtime_portrait_json_issues
        else []
    )
    portrait_issues = portrait_semantic_issues + runtime_portrait_json_issues + runtime_portrait_issues
    critical_fields = {
        "persona.decision_patterns",
        "work.workflow_patterns",
        "work.review_preferences",
    }
    runtime_low_confidence_fields = analysis_quality["low_confidence_fields"]
    low_confidence_fields = [
        item for item in runtime_low_confidence_fields if item.get("field_path", "") in critical_fields
    ]
    runtime_review = normalize_runtime_release_review(meta.get("runtime_release_review"))
    release_review_brief = runtime_release_review_brief(runtime_review)
    portraits_review_brief = runtime_portraits_review_brief(runtime_review)
    release_review_issues = runtime_release_review_issues(runtime_review)
    release_decision = runtime_release_decision(runtime_contract, runtime_review)
    release_manifest = load_json(release_manifest_path) if release_manifest_path.exists() else {}
    previous_release_manifest, previous_release_manifest_path = (
        load_previous_release_manifest(bundle_dir) if release_manifest_path.exists() else ({}, "")
    )
    analysis_conflicts = analysis_quality["analysis_conflicts"]
    resolved_conflicts = analysis_quality["resolved_conflicts"]
    resolution_history = analysis_quality["resolution_history"]
    privacy_counts = analysis_quality["privacy_counts"]
    privacy_issues: list[str] = []
    if privacy_counts["private_sensitive"] > 0 or privacy_counts["work_adjacent"] > 0:
        privacy_issues.append("private-sensitive content was excluded from default analysis")
    if privacy_counts["private_sensitive"] > max(privacy_counts["work_related"], 1):
        privacy_issues.append("private-sensitive content outweighs clearly work-related material")

    release_manifest_report = {}
    release_manifest_issues: list[str] = []
    release_compare_report = (
        build_release_compare_report(
            release_manifest,
            previous_release_manifest,
            current_manifest_path=str(release_manifest_path),
            previous_manifest_path=previous_release_manifest_path,
        )
        if release_manifest_path.exists()
        else {}
    )
    release_compare_brief = (
        {
            "has_previous": bool(release_compare_report.get("has_previous")),
            "changed": bool(release_compare_report.get("changed")),
            "headline": str(release_compare_report.get("headline", "")).strip(),
            "items": list(release_compare_report.get("items", [])),
        }
        if release_compare_report
        else {}
    )
    runtime_package = load_json(runtime_package_path) if runtime_package_path.exists() else {}
    stored_runtime_smoke_artifact = load_json(runtime_smoke_path) if runtime_smoke_path.exists() else {}
    stable_runtime_smoke_report = (
        build_runtime_smoke_report(runtime_package)
        if runtime_package and (check_runtime_smoke or check_release_manifest or check_runtime_package or meta.get("state") == "final_confirmed")
        else {}
    )
    stable_runtime_smoke_summary = (
        runtime_smoke_brief(stable_runtime_smoke_report)
        if stable_runtime_smoke_report
        else (
            dict(stored_runtime_smoke_artifact.get("runtime_smoke_brief", {}))
            if stored_runtime_smoke_artifact
            else dict(release_manifest.get("runtime_smoke_summary", {}))
        )
    )
    stored_runtime_release_health_artifact = load_json(runtime_release_health_path) if runtime_release_health_path.exists() else {}
    previous_runtime_smoke, previous_runtime_smoke_path = (
        load_previous_runtime_smoke(bundle_dir)
        if stable_runtime_smoke_report
        else ({}, "")
    )
    expected_runtime_smoke_artifact = {}
    runtime_smoke_compare_report = {}
    runtime_smoke_compare_brief = {}
    if stable_runtime_smoke_report:
        provisional_runtime_smoke_artifact = build_runtime_smoke_artifact(
            stable_runtime_smoke_report,
            runtime_package_path=str(runtime_package_path),
            generated_at=str(meta.get("finalized_at", "") or meta.get("updated_at", "") or meta.get("created_at", "")).strip(),
        )
        runtime_smoke_compare_report = build_runtime_smoke_compare_report(
            provisional_runtime_smoke_artifact,
            previous_runtime_smoke,
            current_runtime_smoke_path=str(runtime_smoke_path),
            previous_runtime_smoke_path=previous_runtime_smoke_path,
        )
        runtime_smoke_compare_brief = {
            "has_previous": bool(runtime_smoke_compare_report.get("has_previous")),
            "changed": bool(runtime_smoke_compare_report.get("changed")),
            "headline": str(runtime_smoke_compare_report.get("headline", "")).strip(),
            "items": list(runtime_smoke_compare_report.get("items", [])),
        }
        expected_runtime_smoke_artifact = build_runtime_smoke_artifact(
            stable_runtime_smoke_report,
            runtime_package_path=str(runtime_package_path),
            generated_at=str(meta.get("finalized_at", "") or meta.get("updated_at", "") or meta.get("created_at", "")).strip(),
            compare_report=runtime_smoke_compare_report,
        )
    stored_runtime_prompt_eval_artifact = load_json(runtime_prompt_eval_path) if runtime_prompt_eval_path.exists() else {}
    stable_runtime_prompt_eval_report = (
        build_runtime_prompt_eval_report(runtime_package)
        if runtime_package and (check_runtime_prompt_eval or check_release_manifest or check_runtime_package or meta.get("state") == "final_confirmed")
        else {}
    )
    stable_runtime_prompt_eval_summary = (
        runtime_prompt_eval_brief(stable_runtime_prompt_eval_report)
        if stable_runtime_prompt_eval_report
        else (
            dict(stored_runtime_prompt_eval_artifact.get("runtime_prompt_eval_brief", {}))
            if stored_runtime_prompt_eval_artifact
            else dict(release_manifest.get("runtime_prompt_eval_summary", {}))
        )
    )
    stable_release_health = build_release_health_summary(
        {
            "runtime_contract_summary": summarize_runtime_contract(runtime_contract),
            "runtime_portraits_summary": summarize_runtime_portraits(runtime_portraits),
            "runtime_release_review_brief": release_review_brief,
            "runtime_release_decision": release_decision,
            "release_compare_brief": release_compare_brief,
            "runtime_smoke_summary": stable_runtime_smoke_summary,
            "runtime_prompt_eval_summary": stable_runtime_prompt_eval_summary,
        }
    )
    if not stable_release_health and stored_runtime_release_health_artifact:
        stable_release_health = dict(stored_runtime_release_health_artifact.get("release_health", {}))
    elif not stable_release_health and release_manifest:
        stable_release_health = dict(release_manifest.get("release_health", {}))
    previous_runtime_release_health, previous_runtime_release_health_path = (
        load_previous_runtime_release_health(bundle_dir)
        if stable_release_health
        else ({}, "")
    )
    provisional_runtime_release_health_artifact = (
        build_runtime_release_health_artifact(
            stable_release_health,
            release_manifest_path=str(release_manifest_path),
            runtime_package_path=str(runtime_package_path),
            runtime_smoke_path=str(runtime_smoke_path),
            runtime_prompt_eval_path=str(runtime_prompt_eval_path),
            generated_at=str(meta.get("finalized_at", "") or meta.get("updated_at", "") or meta.get("created_at", "")).strip(),
        )
        if stable_release_health
        else {}
    )
    runtime_release_health_compare_report = (
        build_runtime_release_health_compare_report(
            provisional_runtime_release_health_artifact,
            previous_runtime_release_health,
            current_runtime_release_health_path=str(runtime_release_health_path),
            previous_runtime_release_health_path=previous_runtime_release_health_path,
        )
        if provisional_runtime_release_health_artifact
        else {}
    )
    runtime_release_health_compare_brief = (
        {
            "has_previous": bool(runtime_release_health_compare_report.get("has_previous")),
            "changed": bool(runtime_release_health_compare_report.get("changed")),
            "headline": str(runtime_release_health_compare_report.get("headline", "")).strip(),
            "items": list(runtime_release_health_compare_report.get("items", [])),
        }
        if runtime_release_health_compare_report
        else {}
    )
    expected_runtime_release_health_artifact = (
        build_runtime_release_health_artifact(
            stable_release_health,
            release_manifest_path=str(release_manifest_path),
            runtime_package_path=str(runtime_package_path),
            runtime_smoke_path=str(runtime_smoke_path),
            runtime_prompt_eval_path=str(runtime_prompt_eval_path),
            generated_at=str(meta.get("finalized_at", "") or meta.get("updated_at", "") or meta.get("created_at", "")).strip(),
            compare_report=runtime_release_health_compare_report,
        )
        if stable_release_health
        else {}
    )
    previous_runtime_prompt_eval, previous_runtime_prompt_eval_path = (
        load_previous_runtime_prompt_eval(bundle_dir)
        if stable_runtime_prompt_eval_report
        else ({}, "")
    )
    expected_runtime_prompt_eval_artifact = {}
    runtime_prompt_eval_compare_report = {}
    runtime_prompt_eval_compare_brief = {}
    if stable_runtime_prompt_eval_report:
        provisional_runtime_prompt_eval_artifact = build_runtime_prompt_eval_artifact(
            stable_runtime_prompt_eval_report,
            runtime_package_path=str(runtime_package_path),
            generated_at=str(meta.get("finalized_at", "") or meta.get("updated_at", "") or meta.get("created_at", "")).strip(),
        )
        runtime_prompt_eval_compare_report = build_runtime_prompt_eval_compare_report(
            provisional_runtime_prompt_eval_artifact,
            previous_runtime_prompt_eval,
            current_prompt_eval_path=str(runtime_prompt_eval_path),
            previous_prompt_eval_path=previous_runtime_prompt_eval_path,
        )
        runtime_prompt_eval_compare_brief = {
            "has_previous": bool(runtime_prompt_eval_compare_report.get("has_previous")),
            "changed": bool(runtime_prompt_eval_compare_report.get("changed")),
            "headline": str(runtime_prompt_eval_compare_report.get("headline", "")).strip(),
            "items": list(runtime_prompt_eval_compare_report.get("items", [])),
        }
        expected_runtime_prompt_eval_artifact = build_runtime_prompt_eval_artifact(
            stable_runtime_prompt_eval_report,
            runtime_package_path=str(runtime_package_path),
            generated_at=str(meta.get("finalized_at", "") or meta.get("updated_at", "") or meta.get("created_at", "")).strip(),
            compare_report=runtime_prompt_eval_compare_report,
        )
    release_manifest_report = {
        "evidence_count": len(evidence_items),
        "evidence_balance": evidence_balance,
        "evidence_field_coverage": field_coverage,
        "runtime_contract_summary": summarize_runtime_contract(runtime_contract),
        "runtime_portraits_summary": summarize_runtime_portraits(runtime_portraits),
        "runtime_release_review": runtime_review,
        "runtime_release_review_brief": release_review_brief,
        "runtime_portraits_review_brief": portraits_review_brief,
        "runtime_release_decision": release_decision,
        "release_compare_brief": release_compare_brief,
        "release_health": stable_release_health,
        "runtime_smoke_summary": stable_runtime_smoke_summary,
        "runtime_prompt_eval_summary": stable_runtime_prompt_eval_summary,
    }
    release_manifest_issues = (
        inspect_release_manifest(bundle_dir, release_manifest, meta, release_manifest_report)
        if check_release_manifest and (release_manifest_path.exists() or require_final or meta.get("state") == "final_confirmed")
        else []
    )
    runtime_package_report = {
        "runtime_contract": runtime_contract,
        "runtime_contract_summary": summarize_runtime_contract(runtime_contract),
        "runtime_portraits": runtime_portraits,
        "runtime_portraits_summary": summarize_runtime_portraits(runtime_portraits),
        "release_health": stable_release_health,
        "runtime_smoke_summary": stable_runtime_smoke_summary,
        "runtime_prompt_eval_summary": stable_runtime_prompt_eval_summary,
        "runtime_release_decision": release_decision,
        "runtime_release_review_brief": release_review_brief,
        "release_compare_brief": release_compare_brief,
    }
    runtime_package_issues = (
        inspect_runtime_package(bundle_dir, runtime_package, meta, runtime_package_report, release_manifest)
        if check_runtime_package and (runtime_package_path.exists() or require_final or meta.get("state") == "final_confirmed")
        else []
    )
    runtime_smoke_report = build_runtime_smoke_report(runtime_package) if run_runtime_smoke and runtime_package else {}
    artifact_runtime_smoke_report = (
        dict(stored_runtime_smoke_artifact.get("runtime_smoke_report", {}))
        if stored_runtime_smoke_artifact
        else dict(expected_runtime_smoke_artifact.get("runtime_smoke_report", {}))
    )
    artifact_runtime_smoke_summary = (
        dict(stored_runtime_smoke_artifact.get("runtime_smoke_brief", {}))
        if stored_runtime_smoke_artifact
        else dict(expected_runtime_smoke_artifact.get("runtime_smoke_brief", {}))
    )
    runtime_smoke_report = runtime_smoke_report if run_runtime_smoke else artifact_runtime_smoke_report
    runtime_smoke_issues = list(runtime_smoke_report.get("issues", [])) if runtime_smoke_report else []
    runtime_smoke_summary = (
        runtime_smoke_brief(runtime_smoke_report)
        if run_runtime_smoke
        else artifact_runtime_smoke_summary
    )
    runtime_smoke_artifact = stored_runtime_smoke_artifact if stored_runtime_smoke_artifact else expected_runtime_smoke_artifact
    runtime_smoke_artifact_issues = (
        inspect_runtime_smoke_artifact(stored_runtime_smoke_artifact, expected_runtime_smoke_artifact)
        if check_runtime_smoke and (runtime_smoke_path.exists() or require_final or meta.get("state") == "final_confirmed")
        else []
    )
    runtime_release_health = (
        dict(stored_runtime_release_health_artifact.get("release_health", {}))
        if stored_runtime_release_health_artifact
        else stable_release_health
    )
    runtime_release_health_artifact = (
        stored_runtime_release_health_artifact
        if stored_runtime_release_health_artifact
        else expected_runtime_release_health_artifact
    )
    runtime_release_health_artifact_issues = (
        inspect_runtime_release_health_artifact(stored_runtime_release_health_artifact, expected_runtime_release_health_artifact)
        if check_runtime_package and (runtime_release_health_path.exists() or require_final or meta.get("state") == "final_confirmed")
        else []
    )
    prompt_eval_cases_path = Path(prompt_eval_cases_file).resolve() if prompt_eval_cases_file else None
    prompt_eval_cases_config, prompt_eval_case_source = load_runtime_prompt_eval_cases(prompt_eval_cases_path)
    runtime_prompt_eval_report = (
        build_runtime_prompt_eval_report(
            runtime_package,
            cases_config=prompt_eval_cases_config,
            case_source=prompt_eval_case_source,
            mode=prompt_eval_mode,
            model_command=prompt_eval_model_command,
        )
        if run_prompt_eval and runtime_package
        else {}
    )
    artifact_runtime_prompt_eval_report = (
        dict(stored_runtime_prompt_eval_artifact.get("runtime_prompt_eval_report", {}))
        if stored_runtime_prompt_eval_artifact
        else dict(expected_runtime_prompt_eval_artifact.get("runtime_prompt_eval_report", {}))
    )
    artifact_runtime_prompt_eval_summary = (
        dict(stored_runtime_prompt_eval_artifact.get("runtime_prompt_eval_brief", {}))
        if stored_runtime_prompt_eval_artifact
        else dict(expected_runtime_prompt_eval_artifact.get("runtime_prompt_eval_brief", {}))
    )
    runtime_prompt_eval_report = runtime_prompt_eval_report if run_prompt_eval else artifact_runtime_prompt_eval_report
    runtime_prompt_eval_decision = dict(runtime_prompt_eval_report.get("decision", {})) if runtime_prompt_eval_report else {}
    runtime_prompt_eval_issues = list(runtime_prompt_eval_report.get("issues", [])) if runtime_prompt_eval_report else []
    runtime_prompt_eval_blocking_issues = list(runtime_prompt_eval_report.get("blocking_issues", [])) if runtime_prompt_eval_report else []
    runtime_prompt_eval_summary = (
        runtime_prompt_eval_brief(runtime_prompt_eval_report)
        if run_prompt_eval
        else artifact_runtime_prompt_eval_summary
    )
    runtime_prompt_eval_artifact = stored_runtime_prompt_eval_artifact if stored_runtime_prompt_eval_artifact else expected_runtime_prompt_eval_artifact
    runtime_prompt_eval_artifact_issues = (
        inspect_runtime_prompt_eval_artifact(stored_runtime_prompt_eval_artifact, expected_runtime_prompt_eval_artifact)
        if check_runtime_prompt_eval and (runtime_prompt_eval_path.exists() or require_final or meta.get("state") == "final_confirmed")
        else []
    )

    base_ok = (
        not missing
        and meta.get("state") in {"draft_generated", "final_confirmed"}
        and bool(evidence_items)
        and not runtime_contract_issues
        and not portrait_issues
        and not release_manifest_issues
        and not runtime_package_issues
        and not runtime_release_health_artifact_issues
        and not runtime_smoke_artifact_issues
        and not runtime_prompt_eval_artifact_issues
        and not runtime_smoke_issues
        and not runtime_prompt_eval_blocking_issues
    )
    final_quality_issues: list[str] = []
    if require_final:
        if evidence_balance["persona"] < 2:
            final_quality_issues.append("persona evidence is too sparse for final release")
        if evidence_balance["work"] < 2:
            final_quality_issues.append("work evidence is too sparse for final release")
        if len(field_coverage["persona"]) < 2:
            final_quality_issues.append("persona evidence is not distributed across enough fields")
        if len(field_coverage["work"]) < 2:
            final_quality_issues.append("work evidence is not distributed across enough fields")
        if analysis_conflicts:
            final_quality_issues.append("analysis conflicts must be resolved before final release")
        if low_confidence_fields:
            final_quality_issues.append("critical analysis fields remain low confidence")
        if privacy_counts["private_sensitive"] > max(privacy_counts["work_related"], 1):
            final_quality_issues.append("private-sensitive content dominates the bundle")
        if runtime_contract.get("final_contract_issues", []):
            final_quality_issues.extend(runtime_contract.get("final_contract_issues", []))
        if release_review_issues:
            final_quality_issues.extend(release_review_issues)
        if release_manifest_issues:
            final_quality_issues.extend(release_manifest_issues)
        if runtime_package_issues:
            final_quality_issues.extend(runtime_package_issues)
        if runtime_release_health_artifact_issues:
            final_quality_issues.extend(runtime_release_health_artifact_issues)
        if runtime_smoke_artifact_issues:
            final_quality_issues.extend(runtime_smoke_artifact_issues)
        if runtime_prompt_eval_artifact_issues:
            final_quality_issues.extend(runtime_prompt_eval_artifact_issues)
        if runtime_smoke_issues:
            final_quality_issues.extend(runtime_smoke_issues)
        if runtime_prompt_eval_blocking_issues:
            final_quality_issues.extend(runtime_prompt_eval_blocking_issues)

    final_ok = (
        base_ok
        and meta.get("state") == "final_confirmed"
        and len(evidence_items) >= 4
        and not placeholders
        and not final_quality_issues
    )

    return {
        "ok": final_ok if require_final else base_ok,
        "bundle_dir": str(bundle_dir),
        "missing_files": missing,
        "state": meta.get("state", ""),
        "evidence_count": len(evidence_items),
        "evidence_balance": evidence_balance,
        "evidence_field_coverage": field_coverage,
        "require_final": require_final,
        "final_placeholders": placeholders,
        "final_quality_issues": final_quality_issues,
        "analysis_conflicts": analysis_conflicts,
        "resolved_conflicts": resolved_conflicts,
        "resolution_history": resolution_history,
        "low_confidence_fields": low_confidence_fields,
        "runtime_low_confidence_fields": runtime_low_confidence_fields,
        "runtime_required_caveats": runtime_contract.get("known_unknowns", {}).get("required_items", []),
        "runtime_minor_caveats": runtime_contract.get("known_unknowns", {}).get("minor_items", []),
        "runtime_contract": runtime_contract,
        "runtime_contract_summary": summarize_runtime_contract(runtime_contract),
        "runtime_portraits": runtime_portraits,
        "runtime_portraits_summary": summarize_runtime_portraits(runtime_portraits),
        "runtime_contract_final_issues": runtime_contract.get("final_contract_issues", []),
        "runtime_release_review": runtime_review,
        "runtime_release_review_brief": release_review_brief,
        "runtime_portraits_review_brief": portraits_review_brief,
        "runtime_release_decision": release_decision,
        "runtime_release_review_issues": release_review_issues,
        "release_manifest": release_manifest,
        "release_manifest_issues": release_manifest_issues,
        "release_compare_report": release_compare_report,
        "release_compare_brief": release_compare_brief,
        "runtime_package": runtime_package,
        "runtime_package_issues": runtime_package_issues,
        "runtime_release_health": runtime_release_health,
        "runtime_release_health_artifact": runtime_release_health_artifact,
        "runtime_release_health_artifact_issues": runtime_release_health_artifact_issues,
        "runtime_release_health_compare_report": runtime_release_health_compare_report,
        "runtime_release_health_compare_brief": runtime_release_health_compare_brief,
        "runtime_smoke_artifact": runtime_smoke_artifact,
        "runtime_smoke_artifact_issues": runtime_smoke_artifact_issues,
        "runtime_smoke_compare_report": runtime_smoke_compare_report,
        "runtime_smoke_compare_brief": runtime_smoke_compare_brief,
        "runtime_prompt_eval_artifact": runtime_prompt_eval_artifact,
        "runtime_prompt_eval_artifact_issues": runtime_prompt_eval_artifact_issues,
        "runtime_prompt_eval_compare_report": runtime_prompt_eval_compare_report,
        "runtime_prompt_eval_compare_brief": runtime_prompt_eval_compare_brief,
        "runtime_smoke_report": runtime_smoke_report,
        "runtime_smoke_summary": runtime_smoke_summary,
        "runtime_smoke_issues": runtime_smoke_issues,
        "runtime_prompt_eval_report": runtime_prompt_eval_report,
        "runtime_prompt_eval_decision": runtime_prompt_eval_decision,
        "runtime_prompt_eval_summary": runtime_prompt_eval_summary,
        "runtime_prompt_eval_issues": runtime_prompt_eval_issues,
        "runtime_prompt_eval_blocking_issues": runtime_prompt_eval_blocking_issues,
        "privacy_counts": privacy_counts,
        "privacy_issues": privacy_issues,
        "portrait_issues": portrait_issues,
        "runtime_contract_issues": runtime_contract_issues,
    }


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    report = build_report(
        bundle_dir,
        require_final=args.require_final,
        run_runtime_smoke=args.run_runtime_smoke,
        run_prompt_eval=args.run_prompt_eval,
        prompt_eval_cases_file=args.prompt_eval_cases_file or "",
        prompt_eval_mode=args.prompt_eval_mode,
        prompt_eval_model_command=args.prompt_eval_model_command or "",
    )

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"ok: {report['ok']}")
        print(f"state: {report['state']}")
        print(f"evidence_count: {report['evidence_count']}")
        print(f"evidence_balance: persona={report['evidence_balance']['persona']} work={report['evidence_balance']['work']}")
        if report["require_final"]:
            print("require_final: true")
        if report["final_placeholders"]:
            print("final_placeholders:")
            for item in report["final_placeholders"]:
                print(f"- {item}")
        if report["final_quality_issues"]:
            print("final_quality_issues:")
            for item in report["final_quality_issues"]:
                print(f"- {item}")
        if report["portrait_issues"]:
            print("portrait_issues:")
            for item in report["portrait_issues"]:
                print(f"- {item}")
        if report["analysis_conflicts"]:
            print("analysis_conflicts:")
            for item in report["analysis_conflicts"]:
                print(f"- {item['field_path']}: {item['summary']}")
        if report["resolved_conflicts"]:
            print(f"resolved_conflicts: {len(report['resolved_conflicts'])}")
        if report["resolution_history"]:
            print(f"resolution_history: {len(report['resolution_history'])}")
        if report["low_confidence_fields"]:
            print("low_confidence_fields:")
            for item in report["low_confidence_fields"]:
                print(f"- {item['field_path']}: {item['confidence']}")
        if report["runtime_contract_issues"]:
            print("runtime_contract_issues:")
            for item in report["runtime_contract_issues"]:
                print(f"- {item}")
        if report["runtime_contract_final_issues"]:
            print("runtime_contract_final_issues:")
            for item in report["runtime_contract_final_issues"]:
                print(f"- {item}")
        if report["runtime_contract_summary"]:
            print(
                "runtime_contract_summary: "
                f"required={report['runtime_contract_summary']['has_required_caveats']} "
                f"privacy_limited={report['runtime_contract_summary']['privacy_limited']} "
                f"final_issue_count={report['runtime_contract_summary']['final_issue_count']}"
            )
        if report["runtime_portraits_summary"]:
            print(
                "runtime_portraits_summary: "
                f"modules={len(report['runtime_portraits_summary']['default_modules'])} "
                f"focus={len(report['runtime_portraits_summary']['default_review_focus'])} "
                f"tendencies={len(report['runtime_portraits_summary']['interaction_tendencies'])} "
                f"boundary_policy={report['runtime_portraits_summary']['boundary_policy']}"
            )
        if report["runtime_release_review"]:
            print(
                "runtime_release_review: "
                f"status={report['runtime_release_review']['status']} "
                f"requires_ack={report['runtime_release_review']['requires_ack']}"
            )
            if report["runtime_release_review_brief"]:
                print(
                    "runtime_release_review_brief: "
                    f"severity={report['runtime_release_review_brief']['severity']} "
                    f"headline={report['runtime_release_review_brief']['headline']}"
                )
            if report["runtime_portraits_review_brief"]:
                print(
                    "runtime_portraits_review_brief: "
                    f"severity={report['runtime_portraits_review_brief']['severity']} "
                    f"headline={report['runtime_portraits_review_brief']['headline']}"
                )
            if report["runtime_release_decision"]:
                print(
                    "runtime_release_decision: "
                    f"decision={report['runtime_release_decision']['decision']} "
                    f"reason_codes={','.join(report['runtime_release_decision']['reason_codes'])}"
                )
            drift_summary = report["runtime_release_review"].get("drift_summary", {})
            if drift_summary.get("new_restrictions"):
                print("runtime_review_new_restrictions:")
                for item in drift_summary["new_restrictions"]:
                    print(f"- {item}")
            if drift_summary.get("new_uncertainty"):
                print("runtime_review_new_uncertainty:")
                for item in drift_summary["new_uncertainty"]:
                    print(f"- {item}")
            if drift_summary.get("cleared_caveats"):
                print("runtime_review_cleared_caveats:")
                for item in drift_summary["cleared_caveats"]:
                    print(f"- {item}")
        if report["runtime_release_review_issues"]:
            print("runtime_release_review_issues:")
            for item in report["runtime_release_review_issues"]:
                print(f"- {item}")
        if report["release_manifest_issues"]:
            print("release_manifest_issues:")
            for item in report["release_manifest_issues"]:
                print(f"- {item}")
        if report["release_compare_brief"]:
            print(
                "release_compare_brief: "
                f"changed={report['release_compare_brief']['changed']} "
                f"headline={report['release_compare_brief']['headline']}"
            )
        if report["runtime_package_issues"]:
            print("runtime_package_issues:")
            for item in report["runtime_package_issues"]:
                print(f"- {item}")
        if report["runtime_release_health"]:
            print(
                "runtime_release_health: "
                f"ok={report['runtime_release_health']['ok']} "
                f"decision={report['runtime_release_health']['decision']['decision']} "
                f"headline={report['runtime_release_health']['headline']}"
            )
        if report["runtime_release_health_artifact_issues"]:
            print("runtime_release_health_artifact_issues:")
            for item in report["runtime_release_health_artifact_issues"]:
                print(f"- {item}")
        if report["runtime_release_health_compare_brief"]:
            print(
                "runtime_release_health_compare_brief: "
                f"changed={report['runtime_release_health_compare_brief']['changed']} "
                f"headline={report['runtime_release_health_compare_brief']['headline']}"
            )
        if report["runtime_smoke_compare_brief"]:
            print(
                "runtime_smoke_compare_brief: "
                f"changed={report['runtime_smoke_compare_brief']['changed']} "
                f"headline={report['runtime_smoke_compare_brief']['headline']}"
            )
        if report["runtime_smoke_artifact_issues"]:
            print("runtime_smoke_artifact_issues:")
            for item in report["runtime_smoke_artifact_issues"]:
                print(f"- {item}")
        if report["runtime_prompt_eval_compare_brief"]:
            print(
                "runtime_prompt_eval_compare_brief: "
                f"changed={report['runtime_prompt_eval_compare_brief']['changed']} "
                f"headline={report['runtime_prompt_eval_compare_brief']['headline']}"
            )
        if report["runtime_prompt_eval_artifact_issues"]:
            print("runtime_prompt_eval_artifact_issues:")
            for item in report["runtime_prompt_eval_artifact_issues"]:
                print(f"- {item}")
        if report["runtime_smoke_summary"]:
            print(
                "runtime_smoke_summary: "
                f"ok={report['runtime_smoke_summary']['ok']} "
                f"headline={report['runtime_smoke_summary']['headline']}"
            )
        if report["runtime_smoke_issues"]:
            print("runtime_smoke_issues:")
            for item in report["runtime_smoke_issues"]:
                print(f"- {item}")
        if report["runtime_prompt_eval_summary"]:
            print(
                "runtime_prompt_eval_summary: "
                f"ok={report['runtime_prompt_eval_summary']['ok']} "
                f"mode={report['runtime_prompt_eval_summary']['mode']} "
                f"decision={report['runtime_prompt_eval_summary']['decision']} "
                f"score={report['runtime_prompt_eval_summary']['score']} "
                f"headline={report['runtime_prompt_eval_summary']['headline']}"
            )
        if report["runtime_prompt_eval_issues"]:
            print("runtime_prompt_eval_issues:")
            for item in report["runtime_prompt_eval_issues"]:
                print(f"- {item}")
        if report["privacy_issues"]:
            print("privacy_issues:")
            for item in report["privacy_issues"]:
                print(f"- {item}")
        if report["missing_files"]:
            print("missing_files:")
            for path in report["missing_files"]:
                print(f"- {path}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
