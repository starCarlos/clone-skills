from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_runtime_smoke_artifact,
    build_runtime_smoke_compare_report,
    build_runtime_smoke_report,
    load_json,
    load_previous_runtime_smoke,
    runtime_smoke_brief,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run runtime smoke checks for a finalized colleague-clone runtime package.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to check.")
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

    smoke_report = build_runtime_smoke_report(load_json(runtime_package_path))
    previous_runtime_smoke, previous_runtime_smoke_path = load_previous_runtime_smoke(bundle_dir)
    provisional_runtime_smoke_artifact = build_runtime_smoke_artifact(
        smoke_report,
        runtime_package_path=str(runtime_package_path),
    )
    runtime_smoke_compare_report = build_runtime_smoke_compare_report(
        provisional_runtime_smoke_artifact,
        previous_runtime_smoke,
        current_runtime_smoke_path=str(bundle_dir / "runtime_smoke.json"),
        previous_runtime_smoke_path=previous_runtime_smoke_path,
    )
    payload = {
        "ok": bool(smoke_report.get("ok", False)),
        "bundle_dir": str(bundle_dir),
        "runtime_package_path": str(runtime_package_path),
        "runtime_smoke_report": smoke_report,
        "runtime_smoke_brief": runtime_smoke_brief(smoke_report),
        "runtime_smoke_compare_report": runtime_smoke_compare_report,
        "runtime_smoke_compare_brief": {
            "has_previous": bool(runtime_smoke_compare_report.get("has_previous")),
            "changed": bool(runtime_smoke_compare_report.get("changed")),
            "headline": str(runtime_smoke_compare_report.get("headline", "")).strip(),
            "items": list(runtime_smoke_compare_report.get("items", [])),
        },
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        brief = payload["runtime_smoke_brief"]
        print(f"ok: {payload['ok']}")
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
