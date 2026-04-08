#!/usr/bin/env python3
"""Validate a person skill directory against acceptance criteria.

Checks structure, content quality, and completeness per acceptance.md.
Outputs PASS/FAIL with a detailed report.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from utils import load_jsonl, setup_logging

logger = setup_logging(__name__)

PLACEHOLDER_PATTERNS = [
    r"待补充",
    r"待完善",
    r"TBD",
    r"TODO",
    r"pending",
    r"未覆盖",
    r"无法判断",
    r"placeholder",
    r"\[待填\]",
    r"\[TBD\]",
]


def check_file_exists(path: Path, label: str) -> tuple[bool, str]:
    if path.exists() and path.stat().st_size > 0:
        return True, f"PASS: {label} exists and is non-empty"
    if path.exists():
        return False, f"FAIL: {label} exists but is empty"
    return False, f"FAIL: {label} not found at {path}"


def check_optional_file_exists(path: Path, label: str) -> tuple[bool, str]:
    if path.exists() and path.stat().st_size > 0:
        return True, f"PASS: {label} exists and is non-empty"
    return False, f"WARN: {label} not found at {path}"


def check_min_items(text: str, pattern: str, min_count: int, label: str) -> tuple[bool, str]:
    """Check that *pattern* matches at least *min_count* times in *text*."""
    matches = re.findall(pattern, text, re.MULTILINE)
    count = len(matches)
    if count >= min_count:
        return True, f"PASS: {label} — found {count} (>= {min_count})"
    return False, f"FAIL: {label} — found {count} (< {min_count} required)"


def check_no_placeholders(text: str, label: str) -> tuple[bool, str]:
    """Check that no placeholder text remains."""
    found = []
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            found.append(pat)
    if not found:
        return True, f"PASS: {label} — no placeholder text"
    return False, f"FAIL: {label} — found placeholders: {', '.join(found)}"


def check_boundary_declaration(text: str) -> tuple[bool, str]:
    """Check system_prompt contains boundary/constraint declaration."""
    boundary_markers = [
        "能力圈", "边界", "约束", "constraint", "boundary",
        "超出", "不擅长", "不确定", "局限",
        "beyond my", "outside my", "limitation",
    ]
    lower = text.lower()
    for marker in boundary_markers:
        if marker.lower() in lower:
            return True, "PASS: system_prompt contains boundary declaration"
    return False, "FAIL: system_prompt missing boundary/constraint declaration"


def check_skill_structure(text: str) -> list[tuple[bool, str]]:
    """Check SKILL.md includes key routing/guardrail sections."""
    required_sections = [
        ("Quick 模式", "SKILL.md contains Quick mode"),
        ("Full 模式", "SKILL.md contains Full mode"),
        ("不适用 / 降级场景", "SKILL.md contains inapplicable/degrade section"),
        ("反偏见条款", "SKILL.md contains anti-bias clause"),
    ]
    results = []
    for marker, label in required_sections:
        ok = marker in text
        results.append((ok, f"{'PASS' if ok else 'WARN'}: {label}"))
    return results


def check_extraction_coverage(items: list[dict], strict: bool = False) -> list[tuple[bool, str]]:
    """Check extraction field coverage.

    Default threshold: 50% (raised from 30%).
    Strict mode: 80%.
    For large corpora (>500 items, typical of forum/tweet archives) short
    posts rarely trigger keyword matches, so we relax the threshold.
    """
    fields = [
        "keywords", "models", "values", "reasoning",
        "decision_style", "language_fingerprint", "blindspots",
    ]
    results = []
    total = len(items)
    # Large corpora have many micro-posts; relax threshold
    if total > 500:
        threshold = 0.20 if not strict else 0.40
    else:
        threshold = 0.50 if not strict else 0.80
    for field in fields:
        count = sum(1 for it in items if it.get(field))
        ratio = count / total if total > 0 else 0
        ok = ratio > threshold
        status = "PASS" if ok else "WARN"
        results.append(
            (ok, f"{status}: extractions.{field} coverage = {count}/{total} ({ratio:.0%}) [threshold={threshold:.0%}]")
        )
    return results


def check_evidence_anchor_coverage(
    items: list[dict],
    root_anchor_exists: bool,
    strict: bool = False,
) -> tuple[bool, str]:
    total = len(items)
    if total == 0:
        return False, "WARN: evidence anchor coverage skipped because extractions are empty"

    count = sum(1 for item in items if item.get("evidence_anchors"))
    ratio = count / total
    if total > 500:
        threshold = 0.20 if not strict else 0.40
    else:
        threshold = 0.35 if not strict else 0.60

    if root_anchor_exists and count == 0:
        return (
            False,
            "FAIL: analysis/extractions.jsonl has 0 embedded evidence_anchors even though evidence_anchors.md exists",
        )
    if ratio >= threshold:
        return True, f"PASS: extractions.evidence_anchors coverage = {count}/{total} ({ratio:.0%}) [threshold={threshold:.0%}]"
    status = "WARN" if count > 0 else "FAIL"
    return False, f"{status}: extractions.evidence_anchors coverage = {count}/{total} ({ratio:.0%}) [threshold={threshold:.0%}]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a person skill directory.")
    parser.add_argument("--skill-dir", required=True, help="person skill directory")
    parser.add_argument("--out", default="", help="optional output report path")
    parser.add_argument("--strict", action="store_true", help="use strict thresholds (80%% coverage)")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    if not skill_dir.exists():
        raise SystemExit(f"skill directory not found: {skill_dir}")

    results: list[tuple[bool, str]] = []

    # --- Structure checks ---
    results.append(check_file_exists(skill_dir / "SKILL.md", "SKILL.md"))
    results.append(check_file_exists(skill_dir / "thinking_profile.md", "thinking_profile.md"))
    results.append(check_file_exists(skill_dir / "system_prompt.md", "system_prompt.md"))
    results.append(check_optional_file_exists(skill_dir / "evaluation_plan.md", "evaluation_plan.md"))
    results.append(check_optional_file_exists(skill_dir / "evaluation_report.md", "evaluation_report.md"))

    # --- Content quality: SKILL.md ---
    skill_md_path = skill_dir / "SKILL.md"
    if skill_md_path.exists():
        skill_text = skill_md_path.read_text(encoding="utf-8", errors="ignore")
        results.append(check_no_placeholders(skill_text, "SKILL.md"))
        results.extend(check_skill_structure(skill_text))

    # --- Content quality: thinking_profile ---
    tp_path = skill_dir / "thinking_profile.md"
    if tp_path.exists():
        tp_text = tp_path.read_text(encoding="utf-8", errors="ignore")

        # Core beliefs >= 3
        results.append(check_min_items(
            tp_text, r"^[-*]\s+.{10,}", 3, "core beliefs (bullet points >= 3)"
        ))

        # Mental models >= 8
        # Count section headers + bullet items under model sections
        model_section = ""
        in_model = False
        for line in tp_text.splitlines():
            if re.match(r"^#{1,3}\s.*(模型|框架|model|framework)", line, re.IGNORECASE):
                in_model = True
                continue
            if in_model and re.match(r"^#{1,3}\s", line):
                in_model = False
            if in_model:
                model_section += line + "\n"
        model_items = re.findall(r"^(?:[-*]|\d+\.)\s+.{5,}", model_section, re.MULTILINE)
        ok = len(model_items) >= 8
        results.append((
            ok,
            f"{'PASS' if ok else 'FAIL'}: mental models — found {len(model_items)} (>= 8 required)"
        ))

        # No placeholders
        results.append(check_no_placeholders(tp_text, "thinking_profile.md"))

    # --- Content quality: system_prompt ---
    sp_path = skill_dir / "system_prompt.md"
    if sp_path.exists():
        sp_text = sp_path.read_text(encoding="utf-8", errors="ignore")
        results.append(check_boundary_declaration(sp_text))
        results.append(check_no_placeholders(sp_text, "system_prompt.md"))

    # --- Evidence anchors ---
    ea_path = skill_dir / "evidence_anchors.md"
    root_anchor_exists = ea_path.exists()
    if ea_path.exists():
        ea_text = ea_path.read_text(encoding="utf-8", errors="ignore")
        anchor_count = len(re.findall(r"^\d+\.\s", ea_text, re.MULTILINE))
        ok = anchor_count > 0
        results.append((ok, f"{'PASS' if ok else 'FAIL'}: evidence_anchors — {anchor_count} entries"))
    else:
        results.append((False, "WARN: evidence_anchors.md not found"))

    # --- Extractions coverage ---
    ext_path = skill_dir / "analysis" / "extractions.jsonl"
    if ext_path.exists():
        items = load_jsonl(ext_path)
        if items:
            results.extend(check_extraction_coverage(items, strict=args.strict))
            results.append(check_evidence_anchor_coverage(items, root_anchor_exists, strict=args.strict))
        else:
            results.append((False, "WARN: extractions.jsonl is empty"))
    else:
        results.append((False, "WARN: analysis/extractions.jsonl not found"))

    # --- Build report ---
    pass_count = sum(1 for ok, _ in results if ok)
    warn_count = sum(1 for _, msg in results if msg.startswith("WARN:"))
    fail_count = sum(1 for _, msg in results if msg.startswith("FAIL:"))
    overall = "PASS" if fail_count == 0 else "FAIL"

    report_lines = [
        f"# Validation Report: {skill_dir.name}",
        "",
        f"Overall: **{overall}** ({pass_count} passed, {warn_count} warned, {fail_count} failed)",
        "",
    ]
    for ok, msg in results:
        report_lines.append(f"- {msg}")

    report = "\n".join(report_lines)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        logger.info("[done] report written to %s", out_path)
    else:
        print(report)

    logger.info(
        "[done] %s — %d passed, %d warned, %d failed",
        overall,
        pass_count,
        warn_count,
        fail_count,
    )
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
