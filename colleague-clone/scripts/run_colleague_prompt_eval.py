from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_runtime_prompt_eval_report,
    load_json,
    load_runtime_prompt_eval_cases,
    runtime_prompt_eval_brief,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic prompt eval previews for a finalized colleague-clone runtime package.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to check.")
    parser.add_argument("--cases-file", help="Optional JSON file that defines a custom prompt eval case set.")
    parser.add_argument("--mode", choices=["deterministic", "model"], default="deterministic")
    parser.add_argument("--model-command", help="Executable that reads a prompt-eval JSON payload on stdin and returns {'answer': ...}.")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    runtime_package_path = bundle_dir / "runtime_package.json"
    if not runtime_package_path.exists():
        payload = {
            "ok": False,
            "bundle_dir": str(bundle_dir),
            "issue": "runtime package does not exist",
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    cases_path = Path(args.cases_file).resolve() if args.cases_file else None
    cases_config, case_source = load_runtime_prompt_eval_cases(cases_path)
    prompt_eval_report = build_runtime_prompt_eval_report(
        load_json(runtime_package_path),
        cases_config=cases_config,
        case_source=case_source,
        mode=args.mode,
        model_command=args.model_command or "",
    )
    payload = {
        "ok": bool(prompt_eval_report.get("ok", False)),
        "bundle_dir": str(bundle_dir),
        "runtime_package_path": str(runtime_package_path),
        "runtime_prompt_eval_report": prompt_eval_report,
        "runtime_prompt_eval_brief": runtime_prompt_eval_brief(prompt_eval_report),
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        brief = payload["runtime_prompt_eval_brief"]
        print(f"ok: {payload['ok']}")
        print(f"mode: {brief['mode']}")
        print(f"profile: {brief['profile']}")
        print(f"case_source: {brief['case_source']}")
        print(f"headline: {brief['headline']}")
        if brief["failed_cases"]:
            print("failed_cases:")
            for item in brief["failed_cases"]:
                print(f"- {item}")
        if brief["issues"]:
            print("issues:")
            for item in brief["issues"]:
                print(f"- {item}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
