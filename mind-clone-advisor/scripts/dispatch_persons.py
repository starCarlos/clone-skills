#!/usr/bin/env python3
"""Dispatch mind-clone updates to person skills from a central registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compliance import default_runtime_registry, enforce_build_gate
from utils import get_project_root, load_registry, run_subprocess


def resolve_path(path_str: str, base_dir: Path) -> str:
    if not path_str:
        return ""
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    return str((base_dir / path_str).resolve())


def load_registry_list(path: Path) -> list[dict]:
    data = load_registry(path)
    return data.get("persons", [])


def main() -> int:
    base_dir = get_project_root()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default=default_runtime_registry(),
    )
    parser.add_argument("--mode", default="update", choices=["create", "update", "full"])
    parser.add_argument("--person", default="", help="filter by slug or name")
    parser.add_argument("--out-root", default=str(base_dir.parent))
    parser.add_argument("--skip-compliance-gate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    persons = load_registry_list(Path(args.registry))
    if not persons:
        print("[info] registry empty")
        return 0

    blocked: list[str] = []
    for p in persons:
        if not p.get("enabled", True):
            continue
        name = p.get("name", "").strip()
        slug = p.get("slug", "").strip() or name
        if args.person and args.person not in {name, slug}:
            continue
        if not args.skip_compliance_gate:
            try:
                enforce_build_gate(p, context=f"dispatch:{slug}")
            except SystemExit as exc:
                print(str(exc))
                blocked.append(slug)
                continue

        skill_dir = p.get("skill_dir")
        if not skill_dir:
            skill_dir = str(Path(args.out_root) / slug)

        ingestor = resolve_path(p.get("ingestor", ""), base_dir)
        source_config = resolve_path(p.get("source_config", ""), base_dir)
        input_corpus = resolve_path(p.get("input_corpus", ""), base_dir)

        incremental = bool(p.get("incremental", True))
        since = p.get("since", "")
        overwrite_outputs = bool(p.get("overwrite_outputs", False))

        skill_path = Path(skill_dir)
        exists = skill_path.exists()

        if args.mode in {"create", "full"} and not exists:
            cmd = [
                sys.executable,
                str(base_dir / "scripts" / "build_full_person_skill.py"),
                "--name",
                name,
                "--slug",
                slug,
                "--out-root",
                args.out_root,
            ]
            if ingestor:
                cmd.extend(["--ingestor", ingestor, "--source-config", source_config])
            elif input_corpus:
                cmd.extend(["--input-corpus", input_corpus])
            else:
                raise SystemExit(f"{slug}: need ingestor or input_corpus")
            if overwrite_outputs:
                cmd.append("--overwrite-outputs")
            if args.skip_compliance_gate:
                cmd.append("--skip-compliance-gate")
            run_subprocess(cmd, dry_run=args.dry_run)
            exists = True

        if args.mode in {"update", "full"} and exists:
            if ingestor:
                cmd = [
                    sys.executable,
                    str(base_dir / "scripts" / "run_ingest.py"),
                    "--ingestor",
                    ingestor,
                    "--skill-dir",
                    str(skill_path),
                    "--source-config",
                    source_config,
                ]
                if incremental:
                    cmd.append("--incremental")
                if since:
                    cmd.extend(["--since", since])
                run_subprocess(cmd, dry_run=args.dry_run)
            elif input_corpus:
                # no ingest step, assume plain_text already updated
                pass

            cmd = [
                sys.executable,
                str(base_dir / "scripts" / "rebuild_from_kb.py"),
                "--skill-dir",
                str(skill_path),
            ]
            if overwrite_outputs:
                cmd.append("--overwrite-outputs")
            if args.skip_compliance_gate:
                cmd.append("--skip-compliance-gate")
            run_subprocess(cmd, dry_run=args.dry_run)

    if blocked:
        print(f"[warn] compliance blocked {len(blocked)} person(s): {', '.join(blocked)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
