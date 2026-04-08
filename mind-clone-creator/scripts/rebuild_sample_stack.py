#!/usr/bin/env python3
"""Rebuild the known-good sample stack from bundled example artifacts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

try:
    from stack_discovery import build_optional_stack_summary, build_stack_validation_command
except ModuleNotFoundError:
    from scripts.stack_discovery import build_optional_stack_summary, build_stack_validation_command


def run(command: list[str], workdir: Path) -> None:
    subprocess.run(command, cwd=workdir, check=True)


DEFAULT_SAMPLE_TIMESTAMP = "2026-01-01T09:00:00+08:00"


COMPAT_EXPORT_PREFIXES = {
    "bundle_dir": "working-clone-bundle-v",
    "pipeline_dir": "workflow-blueprint-pipeline-v",
    "runtime_dir": "workflow-runtime-v",
    "personal_skill_dir": "personal-clone-skill-v",
    "workflow_skill_dir": "workflow-clone-skill-v",
}

REWRITABLE_SUFFIXES = {".json", ".md", ".yaml", ".yml", ".txt"}


def iter_versioned_tmp_exports(tmp_root: Path | None = None) -> dict[str, list[Path]]:
    tmp = (tmp_root or Path("/tmp")).resolve()
    categories: dict[str, list[Path]] = {}
    if not tmp.exists():
        return {key: [] for key in COMPAT_EXPORT_PREFIXES}
    for key, prefix in COMPAT_EXPORT_PREFIXES.items():
        categories[key] = sorted(
            [
                path
                for path in tmp.iterdir()
                if path.is_dir() and path.name.startswith(prefix) and re.search(r"-v(\d+)$", path.name)
            ],
            key=lambda item: int(re.search(r"-v(\d+)$", item.name).group(1)),
            reverse=True,
        )
    return categories


def next_shared_tmp_version(tmp_root: Path | None = None) -> int:
    tmp = (tmp_root or Path("/tmp")).resolve()
    highest = 0
    for paths in iter_versioned_tmp_exports(tmp).values():
        for path in paths:
            match = re.search(r"-v(\d+)$", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def build_tmp_retention_report(retain: int, tmp_root: Path | None = None) -> dict[str, object]:
    tmp = (tmp_root or Path("/tmp")).resolve()
    safe_retain = max(1, retain)
    report: dict[str, object] = {
        "tmp_root": str(tmp),
        "retain": safe_retain,
        "categories": {},
        "prunable_total": 0,
    }
    categories = report["categories"]
    assert isinstance(categories, dict)
    for key, paths in iter_versioned_tmp_exports(tmp).items():
        kept = [str(path) for path in paths[:safe_retain]]
        prunable = [str(path) for path in paths[safe_retain:]]
        categories[key] = {
            "prefix": COMPAT_EXPORT_PREFIXES[key],
            "total_versions": len(paths),
            "kept": kept,
            "prunable": prunable,
        }
        report["prunable_total"] = int(report["prunable_total"]) + len(prunable)
    return report


def prune_tmp_exports(retention_report: dict[str, object]) -> dict[str, list[str]]:
    categories = retention_report.get("categories", {})
    if not isinstance(categories, dict):
        return {}
    pruned: dict[str, list[str]] = {}
    for key, payload in categories.items():
        if not isinstance(payload, dict):
            continue
        candidates = payload.get("prunable", [])
        if not isinstance(candidates, list):
            continue
        removed: list[str] = []
        for path_text in candidates:
            path = Path(str(path_text)).resolve()
            if path.exists():
                shutil.rmtree(path)
            removed.append(str(path))
        pruned[str(key)] = removed
    return pruned


def build_export_path_mapping(summary: dict[str, object], exported: dict[str, str]) -> list[tuple[str, str]]:
    mappings: list[tuple[str, str]] = []
    for key in ["workflow_skill_dir", "runtime_dir", "pipeline_dir", "personal_skill_dir", "bundle_dir"]:
        source = str(summary.get(key, "")).strip()
        destination = str(exported.get(key, "")).strip()
        if source and destination:
            mappings.append((source, destination))
    return sorted(mappings, key=lambda item: len(item[0]), reverse=True)


def replace_path_with_boundary(text: str, source: str, destination: str) -> str:
    pattern = re.compile(re.escape(source) + r'(?=$|/|[\s"\'`)\]},:;])')
    return pattern.sub(destination, text)


def rewrite_exported_tree_paths(root: Path, mappings: list[tuple[str, str]]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in REWRITABLE_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for source, destination in mappings:
            updated = replace_path_with_boundary(updated, source, destination)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def export_latest_tmp_compat(
    summary: dict[str, object],
    retain: int,
    prune: bool,
    tmp_root: Path | None = None,
    max_attempts: int = 8,
) -> dict[str, object]:
    tmp_root = (tmp_root or Path("/tmp")).resolve()
    exported: dict[str, str] = {}
    version = 0

    for _ in range(max_attempts):
        version = next_shared_tmp_version(tmp_root)
        exported = {}
        created_paths: list[Path] = []
        try:
            for key, prefix in COMPAT_EXPORT_PREFIXES.items():
                source = Path(str(summary.get(key, ""))).resolve()
                if not source.exists():
                    continue
                destination = tmp_root / f"{prefix}{version}"
                shutil.copytree(source, destination)
                created_paths.append(destination)
                exported[key] = str(destination)
            break
        except FileExistsError:
            for path in reversed(created_paths):
                if path.exists():
                    shutil.rmtree(path)
            continue
    else:
        raise RuntimeError(f"failed to allocate a unique /tmp export version after {max_attempts} attempts")

    mappings = build_export_path_mapping(summary, exported)
    for key in ["bundle_dir", "pipeline_dir", "runtime_dir", "personal_skill_dir", "workflow_skill_dir"]:
        destination_text = str(exported.get(key, "")).strip()
        if destination_text:
            rewrite_exported_tree_paths(Path(destination_text), mappings)
    exported["version"] = str(version)
    retention = build_tmp_retention_report(retain=retain, tmp_root=tmp_root)
    pruned: dict[str, list[str]] = {}
    if prune:
        pruned = prune_tmp_exports(retention)
        retention = build_tmp_retention_report(retain=retain, tmp_root=tmp_root)
    return {
        "exports": exported,
        "retention": retention,
        "pruned": pruned,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild the bundled sample stack into one output root.")
    parser.add_argument("--output-root", default="/tmp/mind-clone-sample-stack")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--skip-export-latest-tmp", action="store_true")
    parser.add_argument(
        "--tmp-retain",
        type=int,
        default=5,
        help="How many versioned /tmp exports to keep per artifact type in the retention report. Minimum 1.",
    )
    parser.add_argument(
        "--prune-tmp",
        action="store_true",
        help="Delete older /tmp/*-vN exports beyond --tmp-retain after the new export completes.",
    )
    parser.add_argument(
        "--timestamp",
        default=DEFAULT_SAMPLE_TIMESTAMP,
        help="Timestamp injected into sample clone_config generation. Defaults to a fixed deterministic sample timestamp.",
    )
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workdir = Path(__file__).resolve().parent.parent
    examples = workdir / "examples" / "ai_engineer"
    output_root = Path(args.output_root).resolve()
    bundle_dir = output_root / "working-clone-bundle"

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    command = [
        "python3",
        str(workdir / "scripts" / "bootstrap_working_clone_bundle.py"),
        "--interview",
        str(examples / "interview_filled.md"),
        "--output-dir",
        str(bundle_dir),
        "--name",
        "AI工程师分身",
        "--profession",
        "AI Engineer",
        "--timestamp",
        args.timestamp,
        "--mind-profile",
        str(examples / "mind_profile.md"),
        "--system-prompt",
        str(examples / "system_prompt.md"),
        "--eval-report",
        str(examples / "eval_report.md"),
        "--research-digest",
        str(examples / "research_digest.md"),
        "--workflow-name",
        "AI工程需求实现蓝图",
        "--work-unit",
        "接到一个新 AI 需求后完成首版实现",
        "--known-context",
        "AI工程师分身 / AI Engineer",
        "--workflow-interview",
        str(examples / "workflow_interview_filled.md"),
        "--execute-safe",
    ]
    run(command, workdir)

    candidate = (
        bundle_dir,
        bundle_dir / "workflow-blueprint-pipeline",
        bundle_dir / "workflow-blueprint-pipeline" / "workflow-runtime-bundle",
        bundle_dir / "personal-clone-skill",
        bundle_dir / "workflow-blueprint-pipeline" / "workflow-clone-skill",
    )
    summary = build_optional_stack_summary(
        bundle_dir=candidate[0],
        pipeline_dir=candidate[1],
        runtime_dir=candidate[2],
        personal_skill_dir=candidate[3],
        workflow_skill_dir=candidate[4],
        selection_mode="sample_stack_build",
    )
    summary_path = output_root / "SAMPLE_STACK_SUMMARY.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    compat_exports: dict[str, str] = {}
    tmp_retention: dict[str, object] = {}
    if not args.skip_export_latest_tmp:
        compat_report = export_latest_tmp_compat(summary, retain=args.tmp_retain, prune=args.prune_tmp)
        compat_exports = dict(compat_report.get("exports", {}))
        tmp_retention = {
            "report": compat_report.get("retention", {}),
            "pruned": compat_report.get("pruned", {}),
        }

    validation_result: dict[str, object] = {"skipped": args.skip_validate}
    if not args.skip_validate:
        proc = subprocess.run(
            build_stack_validation_command(workdir, *candidate),
            cwd=workdir,
            check=False,
            capture_output=True,
            text=True,
        )
        validation_result = json.loads(proc.stdout) if proc.stdout.strip() else {"ok": proc.returncode == 0}
        validation_result["exit_code"] = proc.returncode
        validation_result["ok"] = bool(validation_result.get("ok", proc.returncode == 0))

    report = {
        "output_root": str(output_root),
        "bundle_dir": str(bundle_dir),
        "sample_summary": str(summary_path),
        "stack": summary,
        "latest_tmp_exports": compat_exports,
        "tmp_retention": tmp_retention,
        "validation": validation_result,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    return 0 if bool(validation_result.get("ok", True)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
