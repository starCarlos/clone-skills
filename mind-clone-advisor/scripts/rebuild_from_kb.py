#!/usr/bin/env python3
"""Rebuild analysis + graphs from an existing skill/kb/plain_text."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from compliance import default_runtime_registry, enforce_build_gate, resolve_existing_skill_record
from utils import run_subprocess, setup_logging

logger = setup_logging(__name__)


def _should_block_reason(reason_text: str) -> bool:
    reason = (reason_text or "").lower()
    # Hard block reasons only. Soft markers like subscribe/sign-in are noisy.
    hard_markers = (
        "too_short",
        "garbled_text",
        "page not found",
        "not found",
        "页面没有找到",
        "页面不存在",
        "404",
        "forbidden",
        "access denied",
        "captcha",
        "cloudflare",
        "not available",
    )
    return any(m in reason for m in hard_markers)


def _load_low_quality_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        parts = s.split("\t", 1)
        file_name = parts[0].strip()
        reason_text = parts[1].strip() if len(parts) > 1 else ""
        if file_name and _should_block_reason(reason_text):
            names.add(file_name)
    return {n for n in names if n}


def _load_manifest_file_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        f = (obj.get("file") or "").strip()
        if f:
            names.add(f)
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--registry", default=default_runtime_registry(), help="registry json path")
    parser.add_argument("--name", default="", help="override display name")
    parser.add_argument("--overwrite-outputs", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--scan-quality",
        action="store_true",
        help="scan low-quality plain_text and report before rebuild",
    )
    parser.add_argument(
        "--scan-min-chars",
        type=int,
        default=400,
        help="minimum chars for quality scan",
    )
    parser.add_argument(
        "--min-word-count",
        type=int,
        default=80,
        help="minimum word count for kb manifest inclusion",
    )
    parser.add_argument(
        "--exclude-low-quality",
        action="store_true",
        help="exclude low-quality files from extraction automatically",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="skip validation gate (not recommended)",
    )
    parser.add_argument("--skip-compliance-gate", action="store_true", help="skip compliance gate (not recommended)")
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir)
    base_dir = Path(__file__).resolve().parents[1]
    plain_dir = skill_dir / "kb" / "plain_text"
    analysis_dir = skill_dir / "analysis"
    graph_dir = skill_dir / "graph"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)

    # Clean old graph outputs when overwriting
    if args.overwrite_outputs and graph_dir.exists():
        for f in graph_dir.iterdir():
            if f.is_file():
                f.unlink()
        logger.info(f"[info] cleared old graph outputs in {graph_dir}")

    if not plain_dir.exists():
        raise SystemExit(f"missing plain_text: {plain_dir}")

    # name
    name = args.name or skill_dir.name
    if not args.skip_compliance_gate:
        compliance_record, _ = resolve_existing_skill_record(
            skill_dir,
            Path(args.registry),
            slug=skill_dir.name,
            name=name,
        )
        enforce_build_gate(compliance_record, context=f"rebuild:{skill_dir.name}")

    low_quality_names: set[str] = set()
    if args.scan_quality or args.exclude_low_quality:
        notes_dir = skill_dir / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        out_list = notes_dir / "low_quality.tsv"
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "scan_low_quality.py"),
                "--plain-text-dir",
                str(plain_dir),
                "--min-chars",
                str(args.scan_min_chars),
                "--out",
                str(out_list),
            ]
        )
        low_quality_names = _load_low_quality_names(out_list)
        if out_list.exists() and out_list.read_text(encoding="utf-8").strip():
            logger.warning(f"low-quality candidates listed in {out_list}")

    # 0.5) Auto-convert full_archive → plain_text if full_archive exists
    full_archive_dir = skill_dir / "kb" / "full_archive"
    if full_archive_dir.exists() and any(full_archive_dir.iterdir()):
        existing_plain = list(plain_dir.glob("*.md")) if plain_dir.exists() else []
        if not existing_plain:
            logger.info("[info] converting full_archive → plain_text")
            plain_dir.mkdir(parents=True, exist_ok=True)
            run_subprocess(
                [
                    sys.executable,
                    str(base_dir / "scripts" / "extract_plain_text.py"),
                    "--input-dir",
                    str(full_archive_dir),
                    "--output-dir",
                    str(plain_dir),
                ]
            )

    # 1) manifest
    manifest_path = skill_dir / "kb" / "manifest.jsonl"
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_kb_manifest.py"),
            "--plain-text-dir",
            str(plain_dir),
            "--out",
            str(manifest_path),
            "--min-word-count",
            str(args.min_word_count),
            "--overwrite",
        ]
    )
    manifest_names = _load_manifest_file_names(manifest_path)
    blocked = set(low_quality_names) if args.exclude_low_quality else set()
    include_names = manifest_names - blocked if manifest_names else set()
    effective_plain_dir = plain_dir
    if include_names:
        filtered_dir = skill_dir / "kb" / "plain_text.filtered"
        if filtered_dir.exists():
            shutil.rmtree(filtered_dir)
        filtered_dir.mkdir(parents=True, exist_ok=True)
        for file_name in sorted(include_names):
            src = plain_dir / file_name
            if src.exists():
                shutil.copy2(src, filtered_dir / file_name)
        effective_plain_dir = filtered_dir
        logger.info(
            "[info] using filtered plain_text: kept=%d blocked=%d",
            len(include_names),
            len(blocked),
        )

    # 2) domain config
    domain_config = analysis_dir / "domain_config.json"
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "discover_domain.py"),
            "--input",
            str(effective_plain_dir),
            "--person",
            name,
            "--out",
            str(domain_config),
        ]
    )

    # 3) extract
    extractions = analysis_dir / "extractions.jsonl"
    if extractions.exists() and not args.resume:
        extractions.unlink()
    extract_cmd = [
        sys.executable,
        str(base_dir / "scripts" / "llm_extract.py"),
        "--input",
        str(effective_plain_dir),
        "--output",
        str(extractions),
        "--config",
        str(domain_config),
    ]
    if args.resume:
        extract_cmd.append("--resume")
    run_subprocess(extract_cmd)

    # 4) evidence anchors
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "add_evidence_anchors.py"),
            "--plain-text-dir",
            str(effective_plain_dir),
            "--input",
            str(extractions),
            "--output",
            str(extractions),
            "--config",
            str(domain_config),
        ]
    )
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "enrich_extractions.py"),
            "--skill-dir",
            str(skill_dir),
        ]
    )

    # 5) summarize
    summarize_cmd = [
        sys.executable,
        str(base_dir / "scripts" / "llm_summarize.py"),
        "--input",
        str(extractions),
        "--out-dir",
        str(skill_dir),
        "--name",
        name,
        "--config",
        str(domain_config),
    ]
    if args.overwrite_outputs:
        summarize_cmd.append("--overwrite")
    run_subprocess(summarize_cmd)

    # 6) corpus summary
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_corpus_summary.py"),
            "--input",
            str(extractions),
            "--out-json",
            str(analysis_dir / "corpus_summary.json"),
            "--out-md",
            str(analysis_dir / "corpus_summary.md"),
            "--overwrite",
        ]
    )

    # 7) theme + graphs
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_theme_clusters.py"),
            "--input",
            str(extractions),
            "--out",
            str(skill_dir / "theme_clusters.md"),
            "--config",
            str(domain_config),
        ]
    )
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_thought_graph.py"),
            "--input",
            str(extractions),
            "--out-dir",
            str(graph_dir),
            "--config",
            str(domain_config),
        ]
    )
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_relation_graph.py"),
            "--extractions",
            str(extractions),
            "--plain-text-dir",
            str(effective_plain_dir),
            "--out-dir",
            str(graph_dir),
            "--config",
            str(domain_config),
        ]
    )
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_thought_hierarchy.py"),
            "--input",
            str(extractions),
            "--out-dir",
            str(graph_dir),
            "--config",
            str(domain_config),
        ]
    )
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "build_argument_chains.py"),
            "--plain-text-dir",
            str(effective_plain_dir),
            "--out-dir",
            str(graph_dir),
            "--config",
            str(domain_config),
        ]
    )
    run_subprocess(
        [
            sys.executable,
            str(base_dir / "scripts" / "compute_node_weights.py"),
            "--input",
            str(extractions),
            "--out",
            str(graph_dir / "node_weights.json"),
            "--config",
            str(domain_config),
        ]
    )

    # 8) Ensure helper docs exist for downstream evaluation/maintenance.
    for helper_name in ("rag_plan.md", "evaluation_plan.md"):
        src = skill_dir / "assets" / helper_name
        dst = skill_dir / helper_name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    # 9) evaluation report
    evaluation_plan = skill_dir / "evaluation_plan.md"
    if evaluation_plan.exists():
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "evaluate_person_skill.py"),
                "--skill-dir",
                str(skill_dir),
                "--out",
                str(skill_dir / "evaluation_report.md"),
            ]
        )
    else:
        logger.warning("evaluation plan missing, skipped evaluation: %s", evaluation_plan)

    # 10) validate skill (quality gate)
    if not args.skip_validate:
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "validate_person_skill.py"),
                "--skill-dir",
                str(skill_dir),
                "--out",
                str(skill_dir / "notes" / "validation_report.md"),
            ]
        )

    logger.info(f"[done] rebuilt {skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
