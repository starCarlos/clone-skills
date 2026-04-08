#!/usr/bin/env python3
"""End-to-end builder for a complete person skill.

Pipeline:
1) generate_person_skill.py (skeleton + templates)
2) copy corpus into kb/plain_text
3) discover_domain.py -> analysis/domain_config.json
4) llm_extract.py -> analysis/extractions.jsonl
5) llm_summarize.py -> thinking_profile.md + system_prompt.md
6) graph + argument chains + theme clusters + node weights
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from compliance import (
    add_compliance_fields,
    apply_compliance_fields,
    default_runtime_registry,
    enforce_build_gate,
    lookup_registry_record,
)
from utils import get_project_root, run_subprocess, slugify


def copy_corpus(src_dir: Path, dst_dir: Path) -> int:
    """Copy plain-text corpus files into skill kb/plain_text.

    Supports both .md and .txt (the registry corpus often uses .txt).
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    patterns = ["*.md", "*.txt"]
    files = []
    for pat in patterns:
        files.extend(src_dir.glob(pat))
    for path in sorted(set(files)):
        target = dst_dir / path.name
        if target.exists():
            continue
        shutil.copy2(path, target)
        copied += 1
    return copied


def ensure_root_docs(skill_dir: Path) -> None:
    for name in ("rag_plan.md", "evaluation_plan.md"):
        src = skill_dir / "assets" / name
        dst = skill_dir / name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a complete person skill.")
    parser.add_argument("--name", required=True, help="person display name")
    parser.add_argument("--slug", default="", help="skill folder slug")
    parser.add_argument("--input-corpus", default="", help="plain_text folder")
    parser.add_argument("--ingestor", default="", help="ingestor path/name")
    parser.add_argument("--source-config", default="", help="source config for ingestor")
    parser.add_argument("--registry", default=default_runtime_registry(), help="registry json path")
    parser.add_argument(
        "--out-root",
        default="",
        help="base folder for new skill",
    )
    parser.add_argument("--install-to-codex", action="store_true")
    parser.add_argument("--force", action="store_true", help="overwrite existing skill")
    parser.add_argument(
        "--overwrite-outputs",
        action="store_true",
        help="overwrite thinking_profile/system_prompt",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume extraction instead of overwriting extractions.jsonl",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=1,
        help="start from step N (for resuming after failure)",
    )
    parser.add_argument("--skip-compliance-gate", action="store_true")
    add_compliance_fields(parser)
    args = parser.parse_args()

    name = args.name.strip()
    if not name:
        raise SystemExit("--name is required")

    slug = args.slug.strip() or slugify(name)
    if not slug:
        raise SystemExit("Unable to infer slug from name; provide --slug")

    base_dir = get_project_root()
    out_root = Path(args.out_root) if args.out_root else base_dir.parent
    skill_dir = out_root / slug
    start = args.start_from

    registry_record, _ = lookup_registry_record(
        Path(args.registry),
        skill_dir=skill_dir,
        slug=slug,
        name=name,
    )
    compliance_record = dict(registry_record or {
        "name": name,
        "slug": slug,
        "skill_dir": str(skill_dir.resolve()),
    })
    compliance_record.setdefault("name", name)
    compliance_record.setdefault("slug", slug)
    compliance_record["skill_dir"] = compliance_record.get("skill_dir") or str(skill_dir.resolve())
    compliance_record = apply_compliance_fields(compliance_record, args)
    if not args.skip_compliance_gate:
        enforce_build_gate(compliance_record, context=f"build:{slug}")

    total_steps = 12

    def step(n: int, label: str) -> bool:
        """Print step progress and return True if this step should run."""
        if n < start:
            print(f"  [{n}/{total_steps}] {label} ... skipped (--start-from {start})")
            return False
        print(f"  [{n}/{total_steps}] {label}")
        return True

    # 1) Generate skill skeleton
    if step(1, "Generate skill skeleton"):
        gen_cmd = [
            sys.executable,
            str(base_dir / "scripts" / "generate_person_skill.py"),
            "--name",
            name,
            "--slug",
            slug,
            "--out-root",
            str(out_root),
        ]
        if args.install_to_codex:
            gen_cmd.append("--install-to-codex")
        if args.force:
            gen_cmd.append("--force")
        else:
            gen_cmd.append("--merge")
        run_subprocess(gen_cmd)

    # 2) Ingest or copy corpus into kb/plain_text (self-contained skill)
    dst_dir = skill_dir / "kb" / "plain_text"
    if step(2, "Ingest / copy corpus"):
        if args.ingestor:
            if not args.source_config:
                raise SystemExit("--source-config is required when using --ingestor")
            run_subprocess(
                [
                    sys.executable,
                    str(base_dir / "scripts" / "run_ingest.py"),
                    "--ingestor",
                    args.ingestor,
                    "--skill-dir",
                    str(skill_dir),
                    "--source-config",
                    args.source_config,
                ]
            )
        elif args.input_corpus:
            src_dir = Path(args.input_corpus)
            if not src_dir.exists():
                raise SystemExit(f"corpus not found: {src_dir}")
            if src_dir.resolve() != dst_dir.resolve():
                copied = copy_corpus(src_dir, dst_dir)
                print(f"[info] copied {copied} files into {dst_dir}")
        else:
            raise SystemExit("Provide --input-corpus or --ingestor + --source-config")

    # 2.5) Auto-convert full_archive to plain_text if full_archive exists
    full_archive_dir = skill_dir / "kb" / "full_archive"
    if full_archive_dir.exists() and any(full_archive_dir.iterdir()):
        existing_plain = list(dst_dir.glob("*.md")) if dst_dir.exists() else []
        if not existing_plain:
            if step(2, "Convert full_archive → plain_text"):
                run_subprocess(
                    [
                        sys.executable,
                        str(base_dir / "scripts" / "extract_plain_text.py"),
                        "--input-dir",
                        str(full_archive_dir),
                        "--output-dir",
                        str(dst_dir),
                    ]
                )

    # 3) Build kb manifest (minimal metadata)
    if step(3, "Build kb manifest"):
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "build_kb_manifest.py"),
                "--plain-text-dir",
                str(dst_dir),
                "--out",
                str(skill_dir / "kb" / "manifest.jsonl"),
            ]
        )

    # 4) Discover domain config
    analysis_dir = skill_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    domain_config = analysis_dir / "domain_config.json"
    if step(4, "Discover domain config"):
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "discover_domain.py"),
                "--input",
                str(dst_dir),
                "--person",
                name,
                "--out",
                str(domain_config),
            ]
        )

    # 5) Extract per-article signals
    extractions = analysis_dir / "extractions.jsonl"
    if step(5, "Extract per-article signals"):
        if extractions.exists() and not args.resume:
            extractions.unlink()
        extract_cmd = [
            sys.executable,
            str(base_dir / "scripts" / "llm_extract.py"),
            "--input",
            str(dst_dir),
            "--output",
            str(extractions),
            "--config",
            str(domain_config),
        ]
        if args.resume:
            extract_cmd.append("--resume")
        run_subprocess(extract_cmd)

    # 6) Build classification labels + evidence anchors
    if step(6, "Build labels + evidence anchors"):
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "build_labels.py"),
                "--plain-text-dir",
                str(dst_dir),
                "--config",
                str(domain_config),
                "--out",
                str(analysis_dir / "labels.jsonl"),
            ]
        )
        run_subprocess(
            [
                sys.executable,
                str(base_dir / "scripts" / "add_evidence_anchors.py"),
                "--plain-text-dir",
                str(dst_dir),
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

    # 7) Summarize into thinking_profile + system_prompt
    if step(7, "Summarize thinking_profile + system_prompt"):
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

    # 8) Corpus summary
    if step(8, "Build corpus summary"):
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
            ]
        )

    # 9) Theme clusters + graphs + argument chains + node weights
    graph_dir = skill_dir / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    if step(9, "Build theme clusters + graphs"):
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
                str(dst_dir),
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
                str(dst_dir),
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

    # 10) Ensure helper docs + evidence_anchors.md
    if step(10, "Build evidence anchors + helper docs"):
        ensure_root_docs(skill_dir)
        evidence_anchors_script = base_dir / "scripts" / "build_evidence_anchors_md.py"
        if evidence_anchors_script.exists():
            run_subprocess(
                [
                    sys.executable,
                    str(evidence_anchors_script),
                    "--input",
                    str(extractions),
                    "--out",
                    str(skill_dir / "evidence_anchors.md"),
                ]
            )

    # 11) Run evaluation report
    if step(11, "Run evaluation"):
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

    # 12) Validate skill (quality gate)
    if step(12, "Validate skill"):
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

    print(f"[done] skill={skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
