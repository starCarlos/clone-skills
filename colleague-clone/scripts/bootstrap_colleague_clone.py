from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local colleague-clone pipeline end to end.")
    parser.add_argument("--bundle-dir", required=True, help="Target bundle directory.")
    parser.add_argument("--name", required=True, help="Display name of the target colleague.")
    parser.add_argument("--slug", default="", help="Optional explicit slug.")
    parser.add_argument("--relationship", default="colleague", help="Relationship to the target.")
    parser.add_argument("--org-context", default="", help="Optional organization context.")
    parser.add_argument("--role-summary", default="", help="Optional one-line role summary.")
    parser.add_argument("--subjective-impression", default="", help="Optional free-form impression.")
    parser.add_argument("--personality-tag", action="append", default=[], help="Repeatable personality tag.")
    parser.add_argument("--culture-tag", action="append", default=[], help="Repeatable culture tag.")
    parser.add_argument("--source", action="append", default=[], help="Repeatable local source path.")
    parser.add_argument(
        "--source-kind",
        action="append",
        default=[],
        help="Optional source kind override aligned with each --source.",
    )
    parser.add_argument("--preflight", action="store_true", help="Run inspect diagnostics before init.")
    parser.add_argument(
        "--stop-on-risky-preflight",
        action="store_true",
        help="Stop before init when preflight marks any source as risky.",
    )
    parser.add_argument("--pasted-text", action="append", default=[], help="Repeatable pasted text payload.")
    return parser.parse_args()


def run_step(command: list[str]) -> dict:
    proc = subprocess.run(command, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"command failed: {' '.join(command)}")
    stdout = proc.stdout.strip()
    return json.loads(stdout) if stdout else {"ok": True}


def main() -> int:
    args = parse_args()
    scripts_dir = Path(__file__).resolve().parent
    results: dict[str, dict] = {}

    if args.preflight:
        preflight_command = [sys.executable, str(scripts_dir / "inspect_colleague_sources.py")]
        for value in args.source:
            preflight_command.extend(["--source", value])
        for value in args.source_kind:
            preflight_command.extend(["--source-kind", value])
        preflight_result = run_step(preflight_command)
        results["preflight"] = preflight_result
        risky_sources = [item for item in preflight_result.get("sources", []) if item.get("risk_level") == "risky"]
        if args.stop_on_risky_preflight and risky_sources:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "bundle_dir": args.bundle_dir,
                        "error": "preflight detected risky sources",
                        "steps": results,
                    },
                    ensure_ascii=False,
                )
            )
            return 1

    init_command = [
        sys.executable,
        str(scripts_dir / "init_colleague_intake.py"),
        "--bundle-dir",
        args.bundle_dir,
        "--name",
        args.name,
        "--relationship",
        args.relationship,
    ]
    if args.slug:
        init_command.extend(["--slug", args.slug])
    if args.org_context:
        init_command.extend(["--org-context", args.org_context])
    if args.role_summary:
        init_command.extend(["--role-summary", args.role_summary])
    if args.subjective_impression:
        init_command.extend(["--subjective-impression", args.subjective_impression])
    for value in args.personality_tag:
        init_command.extend(["--personality-tag", value])
    for value in args.culture_tag:
        init_command.extend(["--culture-tag", value])
    for value in args.source:
        init_command.extend(["--source", value])
    for value in args.source_kind:
        init_command.extend(["--source-kind", value])
    for value in args.pasted_text:
        init_command.extend(["--pasted-text", value])

    steps = {
        "init": init_command,
        "normalize": [sys.executable, str(scripts_dir / "normalize_colleague_sources.py"), "--bundle-dir", args.bundle_dir, "--strict"],
        "persona": [sys.executable, str(scripts_dir / "analyze_colleague_persona.py"), "--bundle-dir", args.bundle_dir],
        "work": [sys.executable, str(scripts_dir / "analyze_colleague_work.py"), "--bundle-dir", args.bundle_dir],
        "build": [sys.executable, str(scripts_dir / "build_colleague_skill.py"), "--bundle-dir", args.bundle_dir],
        "validate": [sys.executable, str(scripts_dir / "validate_colleague_skill.py"), "--bundle-dir", args.bundle_dir, "--format", "json"],
    }

    results.update({name: run_step(command) for name, command in steps.items()})
    print(json.dumps({"ok": True, "bundle_dir": args.bundle_dir, "steps": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
