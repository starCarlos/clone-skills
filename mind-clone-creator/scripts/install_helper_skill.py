#!/usr/bin/env python3
"""Install a helper skill only after explicit user confirmation."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any


INSTALLER_SCRIPT = Path("/home/admin_wsl/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py")
DEFAULT_DEST = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"


def build_command(args: argparse.Namespace) -> list[str]:
    if args.github_url:
        return [
            "python3",
            str(INSTALLER_SCRIPT),
            "--url",
            args.github_url,
        ]
    if args.repo and args.path:
        command = [
            "python3",
            str(INSTALLER_SCRIPT),
            "--repo",
            args.repo,
            "--path",
            args.path,
        ]
        if args.ref:
            command += ["--ref", args.ref]
        return command
    if args.skills_package:
        return [
            "npx",
            "skills",
            "add",
            args.skills_package,
            "-g",
            "-y",
        ]
    raise SystemExit("Missing install source. Provide --github-url, --repo with --path, or --skills-package.")


def detect_existing_install(skill_name: str) -> Path | None:
    target = DEFAULT_DEST / skill_name
    return target if target.exists() else None


def render_plan(args: argparse.Namespace, command: list[str], existing: Path | None) -> dict[str, Any]:
    status = "already_installed" if existing else "ready_for_confirmation"
    return {
        "skill_name": args.skill_name,
        "reason": args.reason,
        "status": status,
        "confirmed": args.confirmed == "yes",
        "execute": args.execute,
        "already_installed_path": str(existing) if existing else "",
        "install_command": command,
        "install_command_text": shlex.join(command),
        "execution_rule": "Only execute when the user has explicitly confirmed installation.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install a helper skill only after explicit user confirmation."
    )
    parser.add_argument("--skill-name", required=True, help="Target skill name.")
    parser.add_argument("--reason", default="", help="Why this skill is needed.")
    parser.add_argument("--github-url", help="GitHub URL for skill-installer.")
    parser.add_argument("--repo", help="owner/repo for skill-installer.")
    parser.add_argument("--path", help="Repo path for the skill.")
    parser.add_argument("--ref", default="main", help="Repo ref.")
    parser.add_argument("--skills-package", help="Package spec for `npx skills add`.")
    parser.add_argument(
        "--confirmed",
        choices=["yes", "no"],
        default="no",
        help="Whether the user explicitly confirmed installation.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the install command. Requires --confirmed yes.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format.",
    )
    return parser.parse_args()


def render_text(plan: dict[str, Any]) -> str:
    lines = [
        "# helper_skill_install",
        "",
        f"skill_name: {plan['skill_name']}",
        f"status: {plan['status']}",
        f"reason: {plan['reason']}",
        f"confirmed: {str(plan['confirmed']).lower()}",
        f"execute: {str(plan['execute']).lower()}",
    ]
    if plan["already_installed_path"]:
        lines.append(f"already_installed_path: {plan['already_installed_path']}")
    lines.extend(
        [
            f"install_command: {plan['install_command_text']}",
            f"execution_rule: {plan['execution_rule']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    command = build_command(args)
    existing = detect_existing_install(args.skill_name)
    plan = render_plan(args, command, existing)

    if existing:
        if args.format == "text":
            print(render_text(plan), end="")
        else:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.execute and args.confirmed != "yes":
        raise SystemExit("Refusing to install without explicit confirmation. Re-run with --confirmed yes.")

    if args.execute:
        result = subprocess.run(command, check=False, text=True, capture_output=True)
        plan["returncode"] = result.returncode
        plan["stdout"] = result.stdout.strip()
        plan["stderr"] = result.stderr.strip()
        plan["status"] = "installed" if result.returncode == 0 else "install_failed"
        if args.format == "text":
            print(render_text(plan), end="")
            if result.stdout.strip():
                print(result.stdout.strip())
            if result.stderr.strip():
                print(result.stderr.strip())
        else:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        return result.returncode

    if args.format == "text":
        print(render_text(plan), end="")
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
