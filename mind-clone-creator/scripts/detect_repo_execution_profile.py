#!/usr/bin/env python3
"""Detect lightweight execution profile for the current repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from profession_adapter_runtime import load_adapter


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def exists(workspace: Path, *relative_paths: str) -> bool:
    return any((workspace / rel).exists() for rel in relative_paths)


def detect_profile(workspace: Path, profession: str = "") -> dict:
    repo_type = []
    test_commands: list[list[str]] = []
    run_commands: list[list[str]] = []
    evidence: list[str] = []
    adapter = load_adapter(workspace, profession)

    pyproject = workspace / "pyproject.toml"
    package_json = workspace / "package.json"
    makefile = workspace / "Makefile"

    if pyproject.exists():
        repo_type.append("python")
        evidence.append("pyproject.toml")
        text = read_text(pyproject)
        if "[tool.pytest.ini_options]" in text or "pytest" in text:
            test_commands.append(["pytest", "--collect-only", "-q"])
        if "uv" in text:
            test_commands.append(["uv", "run", "pytest", "--collect-only", "-q"])
        if "hatch" in text:
            run_commands.append(["hatch", "run", "python", "--version"])

    if exists(workspace, "requirements.txt", "setup.py", "tox.ini", "noxfile.py"):
        if "python" not in repo_type:
            repo_type.append("python")
        if (workspace / "tox.ini").exists():
            evidence.append("tox.ini")
            test_commands.append(["tox", "-l"])
        if (workspace / "noxfile.py").exists():
            evidence.append("noxfile.py")
            run_commands.append(["nox", "--list"])
        if (workspace / "requirements.txt").exists():
            evidence.append("requirements.txt")

    if package_json.exists():
        repo_type.append("node")
        evidence.append("package.json")
        text = read_text(package_json)
        if '"test"' in text:
            test_commands.append(["npm", "test", "--", "--help"])
        if '"vitest"' in text:
            test_commands.append(["npx", "vitest", "--help"])
        if '"jest"' in text:
            test_commands.append(["npx", "jest", "--help"])
        if '"dev"' in text:
            run_commands.append(["npm", "run", "dev", "--", "--help"])

    if makefile.exists():
        evidence.append("Makefile")
        text = read_text(makefile)
        if "test:" in text:
            test_commands.append(["make", "test", "-n"])
        if "dev:" in text:
            run_commands.append(["make", "dev", "-n"])

    if exists(workspace, "pnpm-lock.yaml"):
        evidence.append("pnpm-lock.yaml")
        test_commands.append(["pnpm", "test", "--help"])
    if exists(workspace, "yarn.lock"):
        evidence.append("yarn.lock")
        test_commands.append(["yarn", "test", "--help"])

    deduped_tests = []
    test_seen = set()
    for source in (adapter.get("preferred_test_commands", []), test_commands):
        for cmd in source:
            if not isinstance(cmd, list) or not cmd:
                continue
            key = tuple(cmd)
            if key in test_seen:
                continue
            test_seen.add(key)
            deduped_tests.append(cmd)

    deduped_runs = []
    run_seen = set()
    for source in (adapter.get("preferred_run_commands", []), run_commands):
        for cmd in source:
            if not isinstance(cmd, list) or not cmd:
                continue
            key = tuple(cmd)
            if key in run_seen:
                continue
            run_seen.add(key)
            deduped_runs.append(cmd)

    return {
        "repo_type": repo_type or ["unknown"],
        "evidence": evidence,
        "test_command_candidates": deduped_tests,
        "run_command_candidates": deduped_runs,
        "profession_adapter": {
            "matched": bool(adapter),
            "profession": profession,
            "notes": adapter.get("notes", []),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect repository execution profile.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--profession", default="")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    output = Path(args.output)
    profile = detect_profile(workspace, args.profession)
    output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
