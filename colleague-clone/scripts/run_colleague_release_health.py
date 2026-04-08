from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_release_health_summary,
    build_runtime_release_health_artifact,
    build_runtime_release_health_compare_report,
    load_json,
    load_previous_runtime_release_health,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect unified runtime release health for a finalized colleague-clone bundle.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to check.")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    release_manifest_path = bundle_dir / "release_manifest.json"
    runtime_package_path = bundle_dir / "runtime_package.json"
    runtime_smoke_path = bundle_dir / "runtime_smoke.json"
    runtime_prompt_eval_path = bundle_dir / "runtime_prompt_eval.json"
    runtime_release_health_path = bundle_dir / "runtime_release_health.json"

    required_paths = [
        release_manifest_path,
        runtime_package_path,
        runtime_smoke_path,
        runtime_prompt_eval_path,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        payload = {
            "ok": False,
            "bundle_dir": str(bundle_dir),
            "issue": "required finalized runtime artifacts are missing",
            "missing_files": missing,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    release_manifest = load_json(release_manifest_path)
    runtime_package = load_json(runtime_package_path)
    runtime_smoke = load_json(runtime_smoke_path)
    runtime_prompt_eval = load_json(runtime_prompt_eval_path)
    runtime_release_health = (
        load_json(runtime_release_health_path)
        if runtime_release_health_path.exists()
        else build_runtime_release_health_artifact(
            build_release_health_summary(
                {
                    "runtime_contract_summary": dict(release_manifest.get("runtime_contract_summary", {})),
                    "runtime_portraits_summary": dict(release_manifest.get("runtime_portraits_summary", {})),
                    "runtime_release_review_brief": dict(release_manifest.get("runtime_release_review_brief", {})),
                    "runtime_release_decision": dict(release_manifest.get("runtime_release_decision", {})),
                    "release_compare_brief": dict(runtime_package.get("release", {}).get("compare_brief", {})),
                    "runtime_smoke_summary": dict(runtime_smoke.get("runtime_smoke_brief", {})),
                    "runtime_prompt_eval_summary": dict(runtime_prompt_eval.get("runtime_prompt_eval_brief", {})),
                }
            ),
            release_manifest_path=str(release_manifest_path),
            runtime_package_path=str(runtime_package_path),
            runtime_smoke_path=str(runtime_smoke_path),
            runtime_prompt_eval_path=str(runtime_prompt_eval_path),
        )
    )
    previous_runtime_release_health, previous_runtime_release_health_path = load_previous_runtime_release_health(bundle_dir)
    provisional_runtime_release_health = build_runtime_release_health_artifact(
        dict(runtime_release_health.get("release_health", {})),
        release_manifest_path=str(release_manifest_path),
        runtime_package_path=str(runtime_package_path),
        runtime_smoke_path=str(runtime_smoke_path),
        runtime_prompt_eval_path=str(runtime_prompt_eval_path),
        generated_at=str(runtime_release_health.get("generated_at", "")).strip(),
    )
    runtime_release_health_compare_report = build_runtime_release_health_compare_report(
        provisional_runtime_release_health,
        previous_runtime_release_health,
        current_runtime_release_health_path=str(runtime_release_health_path),
        previous_runtime_release_health_path=previous_runtime_release_health_path,
    )
    payload = {
        "ok": bool(runtime_release_health.get("release_health", {}).get("ok", False)),
        "bundle_dir": str(bundle_dir),
        "runtime_release_health_path": str(runtime_release_health_path),
        "runtime_release_health": dict(runtime_release_health.get("release_health", {})),
        "runtime_release_health_compare_report": runtime_release_health_compare_report,
        "runtime_release_health_compare_brief": {
            "has_previous": bool(runtime_release_health_compare_report.get("has_previous")),
            "changed": bool(runtime_release_health_compare_report.get("changed")),
            "headline": str(runtime_release_health_compare_report.get("headline", "")).strip(),
            "items": list(runtime_release_health_compare_report.get("items", [])),
        },
    }

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        summary = payload["runtime_release_health"]
        print(f"ok: {payload['ok']}")
        print(f"decision: {summary['decision']['decision']}")
        print(f"headline: {summary['headline']}")
        compare_brief = payload["runtime_release_health_compare_brief"]
        print(f"compare_changed: {compare_brief['changed']}")
        print(f"compare_headline: {compare_brief['headline']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
