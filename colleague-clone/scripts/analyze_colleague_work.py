from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from colleague_clone_common import (
    find_evidence,
    iter_normalized_records,
    latest_resolution_entry,
    load_json,
    split_records_by_privacy,
    top_terms,
    utc_now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze colleague work signals from normalized records.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to analyze.")
    return parser.parse_args()


def extract_rules(records: list[dict], limit: int = 5) -> list[dict]:
    rules: list[dict] = []
    for record in records:
        text = str(record.get("text", ""))
        for line in text.splitlines():
            stripped = line.strip("-#* ").strip()
            if not stripped:
                continue
            if any(token in stripped for token in ["必须", "不要", "先", "need to", "must", "should"]):
                rules.append(
                    {
                        "summary": stripped[:180],
                        "evidence": [
                            {
                                "record_id": record.get("record_id", ""),
                                "source_id": record.get("source_id", ""),
                                "source_type": record.get("source_type", ""),
                                "quote": stripped[:240],
                                "confidence": record.get("confidence", 1.0),
                            }
                        ],
                    }
                )
            if len(rules) >= limit:
                return rules
    return rules


def detect_workflow_sequence(records: list[dict]) -> list[str]:
    combined = "\n".join(str(record.get("text", "")) for record in records).lower()
    ordered_steps = [
        ("clarify", ["context", "impact", "clarify", "先问", "需求不清"]),
        ("align_owner", ["owner", "同步", "对齐", "确认 owner", "确认负责人"]),
        ("risk_first", ["风险", "止血"]),
        ("plan", ["方案", "plan"]),
        ("checklist", ["checklist", "runbook", "列表", "清单"]),
    ]
    return [step for step, keywords in ordered_steps if any(keyword in combined for keyword in keywords)]


def detect_delivery_formats(records: list[dict]) -> list[str]:
    combined = "\n".join(str(record.get("text", "")) for record in records).lower()
    formats: list[str] = []
    if any(token in combined for token in ["结论前置", "先说结论", "conclusion"]):
        formats.append("conclusion_first")
    if any(token in combined for token in ["列表", "checklist", "table", "bullet"]):
        formats.append("list")
    if any(token in combined for token in ["风险", "待确认"]):
        formats.append("risk_callout")
    return formats


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
    existing_profile_path = bundle_dir / "analysis" / "work_profile.json"
    existing_profile: dict = {}
    existing_overrides: list[dict] = []
    if existing_profile_path.exists():
        existing_profile = load_json(existing_profile_path)
        existing_overrides = existing_profile.get("manual_overrides", [])

    ownership = find_evidence(records, ["负责", "owner", "模块", "系统", "service", "api"])
    workflow = find_evidence(records, ["先", "然后", "最后", "风险", "方案", "checklist", "runbook", "复盘"])
    review = find_evidence(
        records,
        ["幂等", "事务", "n+1", "错误码", "分页", "并发", "兼容", "兼容性", "idempot", "transaction", "error code", "pagination", "concurrency", "compatibility"],
    )
    delivery = find_evidence(records, ["结论前置", "列表", "table", "checklist", "待确认", "风险说明", "先说结论"])
    execution_first = find_evidence(records, ["直接开工", "先做", "先推进", "不用先列风险", "不等对齐"])
    terms = top_terms(records)
    explicit_rules = extract_rules(records)
    workflow_sequence = detect_workflow_sequence(records)
    delivery_formats = detect_delivery_formats(records)
    workflow_resolution = latest_resolution_entry(existing_profile, "work.workflow_patterns")
    delivery_resolution = latest_resolution_entry(existing_profile, "work.delivery_preferences")
    workflow_conflict = bool(workflow and execution_first)
    delivery_conflict = bool(
        find_evidence(records, ["结论前置", "先说结论"])
        and find_evidence(records, ["不要结论", "不用解释", "别写总结"])
    )

    modules = []
    for match in ownership[:3]:
        quote = match["quote"]
        modules.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", quote))
    modules = sorted(set(modules))[:5]

    scope_confidence, scope_reason = infer_confidence(ownership[:2], conflicting=False)
    workflow_confidence, workflow_reason = infer_confidence(workflow[:2] or execution_first[:2], conflicting=workflow_conflict)
    review_confidence, review_reason = infer_confidence(review[:3], conflicting=False)
    delivery_confidence, delivery_reason = infer_confidence(delivery[:2], conflicting=delivery_conflict)

    workflow_conflict_payload = {
        "field_path": "work.workflow_patterns",
        "summary": "Conflicting signals between risk-first planning and execution-first delivery.",
        "evidence": (workflow[:1] + execution_first[:1])[:2],
    }
    delivery_conflict_payload = {
        "field_path": "work.delivery_preferences",
        "summary": "Conflicting signals about whether to lead with a conclusion.",
        "evidence": delivery[:2],
    }
    resolved_conflicts: list[dict] = []

    if workflow_resolution and workflow_conflict:
        workflow_confidence, workflow_reason = (
            0.8,
            f"resolved by manual override: {workflow_resolution.get('resolution_note', '')}",
        )
        workflow_conflict = False
        resolved_conflicts.append(
            build_resolved_conflict(
                workflow_conflict_payload,
                workflow_resolution,
                confidence=workflow_confidence,
                confidence_reason=workflow_reason,
            )
        )
    if delivery_resolution and delivery_conflict:
        delivery_confidence, delivery_reason = (
            0.8,
            f"resolved by manual override: {delivery_resolution.get('resolution_note', '')}",
        )
        delivery_conflict = False
        resolved_conflicts.append(
            build_resolved_conflict(
                delivery_conflict_payload,
                delivery_resolution,
                confidence=delivery_confidence,
                confidence_reason=delivery_reason,
            )
        )

    conflicts: list[dict] = []
    if workflow_conflict:
        conflicts.append(workflow_conflict_payload)
    if delivery_conflict:
        conflicts.append(delivery_conflict_payload)

    profile = {
        "responsibility_scope": {
            "summary": "Ownership signals appear around APIs, modules, or system boundaries." if ownership else "No clear scope signal yet.",
            "modules": modules,
            "confidence": scope_confidence,
            "confidence_reason": scope_reason,
            "evidence": ownership[:2],
        },
        "workflow_patterns": {
            "summary": "Material suggests a stepwise workflow with risk-first or sequence-first language." if workflow else "No stable workflow pattern yet.",
            "operating_sequence": workflow_sequence,
            "steps_hint": [match["quote"] for match in workflow[:3]],
            "confidence": workflow_confidence,
            "confidence_reason": workflow_reason,
            "evidence": workflow[:2],
        },
        "review_preferences": {
            "summary": "Recurring review focus areas appear in technical correctness checks." if review else "No stable review focus yet.",
            "focus_areas": [
                token
                for token in ["幂等", "事务", "N+1", "错误码", "分页", "并发", "兼容性", "idempotency", "transaction", "error code", "pagination", "concurrency", "compatibility"]
                if any(token.lower() in item["quote"].lower() for item in review)
            ],
            "confidence": review_confidence,
            "confidence_reason": review_reason,
            "evidence": review[:3],
        },
        "delivery_preferences": {
            "summary": "Delivery style favors concise structure with risk or checklist framing." if delivery else "No delivery preference signal yet.",
            "format_preferences": delivery_formats,
            "confidence": delivery_confidence,
            "confidence_reason": delivery_reason,
            "evidence": delivery[:2],
        },
        "domain_knowledge": terms,
        "explicit_rules": explicit_rules,
        "stable_patterns": [
            {
                "label": "technical review focus",
                "summary": "Highlights technical correctness concerns such as idempotency, transactions, or query shape.",
                "evidence": review[:2],
            }
            if review
            else {
                "label": "workflow emphasis",
                "summary": "Uses sequence language to structure work before delivery.",
                "evidence": workflow[:2],
            }
            if workflow
            else {
                "label": "limited work evidence",
                "summary": "Work evidence is still sparse in the current corpus.",
                "evidence": [],
            }
        ],
        "conditional_patterns": [],
        "conflicts": conflicts,
        "resolved_conflicts": resolved_conflicts,
        "resolution_history": existing_profile.get("resolution_history", []),
        "manual_overrides": existing_overrides,
        "privacy_filter": privacy_split["audit"],
    }
    profile["semantic_view"] = {
        "role_scope": {
            "summary": profile["responsibility_scope"]["summary"],
            "modules": profile["responsibility_scope"]["modules"],
            "confidence": profile["responsibility_scope"]["confidence"],
            "confidence_reason": profile["responsibility_scope"]["confidence_reason"],
            "evidence": profile["responsibility_scope"]["evidence"],
        },
        "work_method": {
            "summary": profile["workflow_patterns"]["summary"],
            "operating_sequence": profile["workflow_patterns"]["operating_sequence"],
            "rules_of_thumb": [item.get("summary", "") for item in profile["explicit_rules"][:5] if item.get("summary", "")],
            "confidence": profile["workflow_patterns"]["confidence"],
            "confidence_reason": profile["workflow_patterns"]["confidence_reason"],
            "evidence": profile["workflow_patterns"]["evidence"],
        },
        "review_and_delivery": {
            "summary": "Combines recurring review focus and delivery shape preferences.",
            "focus_areas": profile["review_preferences"]["focus_areas"],
            "format_preferences": profile["delivery_preferences"]["format_preferences"],
            "confidence": min(profile["review_preferences"]["confidence"], profile["delivery_preferences"]["confidence"]),
            "confidence_reason": "derived from review_preferences and delivery_preferences",
            "evidence": (profile["review_preferences"]["evidence"] + profile["delivery_preferences"]["evidence"])[:4],
        },
        "professional_profile": {
            "summary": (
                "Owns concrete work scope, operates with structured steps, and reviews through recurring technical checks."
                if ownership or workflow or review
                else "No stable professional profile signal yet."
            ),
            "scope_modules": profile["responsibility_scope"]["modules"],
            "operating_sequence": profile["workflow_patterns"]["operating_sequence"],
            "review_focus_areas": profile["review_preferences"]["focus_areas"],
            "confidence": min(
                profile["responsibility_scope"]["confidence"],
                profile["workflow_patterns"]["confidence"],
                profile["review_preferences"]["confidence"],
            ),
            "confidence_reason": "derived from responsibility_scope, workflow_patterns, and review_preferences",
            "evidence": (
                profile["responsibility_scope"]["evidence"]
                + profile["workflow_patterns"]["evidence"]
                + profile["review_preferences"]["evidence"]
            )[:5],
        },
    }

    write_json(bundle_dir / "analysis" / "work_profile.json", profile)
    meta["updated_at"] = utc_now_iso()
    write_json(meta_path, meta)
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "stable_pattern_count": len(profile["stable_patterns"]),
                "focus_area_count": len(profile["review_preferences"]["focus_areas"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
