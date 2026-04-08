from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    find_evidence,
    iter_normalized_records,
    latest_resolution_entry,
    load_json,
    split_records_by_privacy,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze colleague persona signals from normalized records.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to analyze.")
    return parser.parse_args()


def detect_coordination_mode(evidence: list[dict]) -> str:
    if not evidence:
        return "unknown"
    text = " ".join(item.get("quote", "") for item in evidence).lower()
    if any(token in text for token in ["owner", "同步", "对齐", "确认", "review", "follow up"]):
        return "owner-alignment"
    return "collaborative"


def detect_boundary_mode(evidence: list[dict]) -> str:
    if not evidence:
        return "implicit_or_unknown"
    return "explicit"


def detect_stress_modes(evidence: list[dict]) -> list[str]:
    if not evidence:
        return []
    text = " ".join(item.get("quote", "") for item in evidence).lower()
    modes: list[str] = []
    if any(token in text for token in ["止血", "回滚", "rollback"]):
        modes.append("rollback-first")
    if any(token in text for token in ["升级", "escalate"]):
        modes.append("escalate-early")
    if any(token in text for token in ["事故", "紧急"]):
        modes.append("incident-command")
    return modes


def extract_conditional_patterns(*, stress: list[dict], boundaries: list[dict], coordination: list[dict]) -> list[dict]:
    patterns: list[dict] = []
    if stress:
        patterns.append(
            {
                "condition": "incident_or_urgent_change",
                "behavior": "stabilize first, then rollback or escalate as needed",
                "evidence": stress[:2],
            }
        )
    if boundaries:
        patterns.append(
            {
                "condition": "unclear_ownership",
                "behavior": "confirm owner before making changes outside scope",
                "evidence": boundaries[:2],
            }
        )
    if coordination:
        patterns.append(
            {
                "condition": "multi_party_work",
                "behavior": "align with owner or stakeholders before execution",
                "evidence": coordination[:2],
            }
        )
    return patterns


def infer_confidence(evidence: list[dict], *, conflicting: bool = False) -> tuple[float, str]:
    if not evidence:
        return 0.2, "no supporting evidence"
    confidence = 0.65 if len(evidence) == 1 else 0.85
    if conflicting:
        confidence = max(0.3, confidence - 0.35)
        return round(confidence, 2), "conflicting signals lower confidence"
    return round(confidence, 2), f"supported by {len(evidence)} evidence item(s)"


def build_resolved_conflict(
    conflict: dict,
    resolution: dict,
    *,
    confidence: float,
    confidence_reason: str,
) -> dict:
    return {
        "field_path": conflict.get("field_path", resolution.get("field_path", "")),
        "summary": conflict.get("summary", ""),
        "evidence": conflict.get("evidence", []),
        "resolution_note": resolution.get("resolution_note", ""),
        "resolved_at": resolution.get("resolved_at", ""),
        "reason": resolution.get("reason", "conflict resolution"),
        "source": resolution.get("source", "conflict_resolution"),
        "confidence_after": confidence,
        "confidence_reason_after": confidence_reason,
    }


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    meta_path = bundle_dir / "meta.json"
    meta = load_json(meta_path)
    all_records = iter_normalized_records(bundle_dir)
    privacy_split = split_records_by_privacy(all_records)
    records = privacy_split["analysis_records"]
    existing_profile_path = bundle_dir / "analysis" / "persona_profile.json"
    existing_profile: dict = {}
    existing_overrides: list[dict] = []
    if existing_profile_path.exists():
        existing_profile = load_json(existing_profile_path)
        existing_overrides = existing_profile.get("manual_overrides", [])

    direct_feedback = find_evidence(records, ["必须", "不要", "fix", "block", "结论", "直接", "先补"])
    question_first = find_evidence(records, ["context", "impact", "为什么", "先问", "先确认", "clarify"])
    coordination = find_evidence(records, ["同步", "对齐", "review", "确认", "owner", "follow up"])
    boundaries = find_evidence(records, ["不是我的", "不负责", "owner", "职责", "边界", "先确认 owner"])
    stress = find_evidence(records, ["紧急", "事故", "止血", "回滚", "rollback", "升级", "escalate"])
    push_first = find_evidence(records, ["直接给结论", "不要反复追问", "直接推进", "不用先问", "别问太多"])
    skip_alignment = find_evidence(records, ["不等对齐", "不用同步", "直接开工", "跳过确认"])

    stress_modes = detect_stress_modes(stress)
    coordination_mode = detect_coordination_mode(coordination)
    boundary_mode = detect_boundary_mode(boundaries)
    decision_resolution = latest_resolution_entry(existing_profile, "persona.decision_patterns")
    collaboration_resolution = latest_resolution_entry(existing_profile, "persona.collaboration_style")
    decision_conflict = bool(question_first and push_first)
    collaboration_conflict = bool(coordination and skip_alignment)
    style_conflict = bool(question_first and direct_feedback and push_first)

    expression_confidence, expression_reason = infer_confidence(direct_feedback[:1] + question_first[:1], conflicting=style_conflict)
    decision_confidence, decision_reason = infer_confidence(
        question_first[:2] or direct_feedback[:2] or push_first[:2],
        conflicting=decision_conflict,
    )
    collaboration_confidence, collaboration_reason = infer_confidence(
        coordination[:2] or skip_alignment[:2],
        conflicting=collaboration_conflict,
    )
    stress_confidence, stress_reason = infer_confidence(stress[:2], conflicting=False)
    boundary_confidence, boundary_reason = infer_confidence(boundaries[:2], conflicting=False)

    decision_conflict_payload = {
        "field_path": "persona.decision_patterns",
        "summary": "Conflicting signals between question-first clarification and push-forward directness.",
        "evidence": (question_first[:1] + push_first[:1])[:2],
    }
    collaboration_conflict_payload = {
        "field_path": "persona.collaboration_style",
        "summary": "Conflicting signals between owner alignment and bypassing coordination.",
        "evidence": (coordination[:1] + skip_alignment[:1])[:2],
    }
    resolved_conflicts: list[dict] = []

    if decision_resolution and decision_conflict:
        decision_confidence, decision_reason = (
            0.8,
            f"resolved by manual override: {decision_resolution.get('resolution_note', '')}",
        )
        decision_conflict = False
        resolved_conflicts.append(
            build_resolved_conflict(
                decision_conflict_payload,
                decision_resolution,
                confidence=decision_confidence,
                confidence_reason=decision_reason,
            )
        )
    if collaboration_resolution and collaboration_conflict:
        collaboration_confidence, collaboration_reason = (
            0.8,
            f"resolved by manual override: {collaboration_resolution.get('resolution_note', '')}",
        )
        collaboration_conflict = False
        resolved_conflicts.append(
            build_resolved_conflict(
                collaboration_conflict_payload,
                collaboration_resolution,
                confidence=collaboration_confidence,
                confidence_reason=collaboration_reason,
            )
        )

    stable_patterns: list[dict] = []
    if question_first:
        stable_patterns.append(
            {
                "label": "question-first disagreement",
                "summary": "Asks for context or impact before agreeing when material is ambiguous.",
                "evidence": question_first[:2],
            }
        )
    if coordination:
        stable_patterns.append(
            {
                "label": "owner-aligned collaboration",
                "summary": "Checks owner or synchronizes with stakeholders before execution.",
                "evidence": coordination[:2],
            }
        )
    if boundaries:
        stable_patterns.append(
            {
                "label": "explicit scope boundary",
                "summary": "Avoids changing out-of-scope areas before confirming ownership.",
                "evidence": boundaries[:2],
            }
        )
    if stress:
        stable_patterns.append(
            {
                "label": "incident stabilization",
                "summary": "Treats incidents with stabilization, rollback, or escalation language first.",
                "evidence": stress[:2],
            }
        )
    if not stable_patterns:
        stable_patterns.append(
            {
                "label": "limited persona evidence",
                "summary": "Persona evidence is still sparse in the current corpus.",
                "evidence": [],
            }
        )

    conflicts: list[dict] = []
    if decision_conflict:
        conflicts.append(decision_conflict_payload)
    if collaboration_conflict:
        conflicts.append(collaboration_conflict_payload)

    profile = {
        "expression_style": {
            "summary": (
                "Direct and conclusion-first when evidence mentions blocking language or explicit action items."
                if direct_feedback
                else "No stable directness pattern yet."
            ),
            "questioning_tendency": "high" if question_first else "unknown",
            "emoji_usage": "none_detected",
            "confidence": expression_confidence,
            "confidence_reason": expression_reason,
            "evidence": direct_feedback[:1] + question_first[:1],
        },
        "decision_patterns": {
            "summary": (
                "Often asks for context before committing to a path." if question_first else "Decision style still under-specified."
            ),
            "priorities": [item for item, present in [("clarity", bool(question_first)), ("correctness", bool(direct_feedback))] if present],
            "disagreement_style": "question-first" if question_first else ("direct" if direct_feedback else "unknown"),
            "confidence": decision_confidence,
            "confidence_reason": decision_reason,
            "evidence": question_first[:2] or direct_feedback[:2],
        },
        "collaboration_style": {
            "summary": "Uses alignment and ownership language in collaboration." if coordination else "No stable collaboration pattern yet.",
            "coordination_mode": coordination_mode,
            "coordination_signals": [match["quote"] for match in coordination[:2]],
            "confidence": collaboration_confidence,
            "confidence_reason": collaboration_reason,
            "evidence": coordination[:2],
        },
        "stress_behaviors": {
            "summary": "Escalation or rollback language appears in high-pressure contexts." if stress else "No stress behavior signal detected.",
            "response_mode": stress_modes,
            "confidence": stress_confidence,
            "confidence_reason": stress_reason,
            "evidence": stress[:2],
        },
        "boundaries_and_taboos": {
            "summary": "Explicitly marks responsibility boundaries." if boundaries else "No clear boundary rule found yet.",
            "boundary_mode": boundary_mode,
            "confidence": boundary_confidence,
            "confidence_reason": boundary_reason,
            "evidence": boundaries[:2],
        },
        "stable_patterns": stable_patterns,
        "conditional_patterns": extract_conditional_patterns(
            stress=stress,
            boundaries=boundaries,
            coordination=coordination,
        ),
        "conflicts": conflicts,
        "resolved_conflicts": resolved_conflicts,
        "resolution_history": existing_profile.get("resolution_history", []),
        "manual_overrides": existing_overrides,
        "privacy_filter": privacy_split["audit"],
    }
    profile["semantic_view"] = {
        "communication_style": {
            "summary": profile["expression_style"]["summary"],
            "questioning_tendency": profile["expression_style"]["questioning_tendency"],
            "disagreement_style": profile["decision_patterns"]["disagreement_style"],
            "confidence": min(profile["expression_style"]["confidence"], profile["decision_patterns"]["confidence"]),
            "confidence_reason": "derived from expression_style and decision_patterns",
            "evidence": (profile["expression_style"]["evidence"] + profile["decision_patterns"]["evidence"])[:3],
        },
        "collaboration_style": {
            "summary": profile["collaboration_style"]["summary"],
            "coordination_mode": profile["collaboration_style"]["coordination_mode"],
            "conditional_patterns": profile["conditional_patterns"],
            "confidence": profile["collaboration_style"]["confidence"],
            "confidence_reason": profile["collaboration_style"]["confidence_reason"],
            "evidence": profile["collaboration_style"]["evidence"],
        },
        "boundary_constraints": {
            "summary": profile["boundaries_and_taboos"]["summary"],
            "boundary_mode": profile["boundaries_and_taboos"]["boundary_mode"],
            "stress_response_modes": profile["stress_behaviors"]["response_mode"],
            "confidence": min(profile["boundaries_and_taboos"]["confidence"], profile["stress_behaviors"]["confidence"]),
            "confidence_reason": "derived from boundaries_and_taboos and stress_behaviors",
            "evidence": (profile["boundaries_and_taboos"]["evidence"] + profile["stress_behaviors"]["evidence"])[:3],
        },
        "temperament_profile": {
            "summary": (
                "Question-first, owner-aware, and boundary-conscious in work interactions."
                if question_first or coordination or boundaries
                else "No stable work-temperament pattern yet."
            ),
            "tendency_tags": [
                tag
                for tag, present in [
                    ("question-first", bool(question_first)),
                    ("owner-aligned", coordination_mode == "owner-alignment"),
                    ("boundary-conscious", boundary_mode == "explicit"),
                    ("rollback-first", "rollback-first" in stress_modes),
                    ("escalate-early", "escalate-early" in stress_modes),
                ]
                if present
            ],
            "pressure_mode": stress_modes or ["unknown"],
            "confidence": min(
                profile["decision_patterns"]["confidence"],
                profile["collaboration_style"]["confidence"],
            ),
            "confidence_reason": "derived from decision_patterns, collaboration_style, and stress_behaviors",
            "evidence": (
                profile["decision_patterns"]["evidence"]
                + profile["collaboration_style"]["evidence"]
                + profile["stress_behaviors"]["evidence"]
            )[:4],
        },
        "family_boundary_profile": {
            "summary": "Family and private-life material is outside the modeled scope; only work-safe boundaries are retained.",
            "policy": "refuse_and_redirect",
            "private_signal_present": bool(
                privacy_split["audit"]["counts"].get("work_adjacent", 0)
                or privacy_split["audit"]["counts"].get("private_sensitive", 0)
            ),
            "allowed_scope": ["role scope", "work method", "review preferences", "communication style", "boundary constraints"],
            "confidence": 1.0,
            "confidence_reason": "policy-driven boundary derived from privacy filtering rules",
            "evidence": profile["boundaries_and_taboos"]["evidence"][:2],
        },
    }

    write_json(bundle_dir / "analysis" / "persona_profile.json", profile)
    meta["updated_at"] = utc_now_iso()
    write_json(meta_path, meta)
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "stable_pattern_count": len(profile["stable_patterns"]),
                "has_question_first_signal": bool(question_first),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
