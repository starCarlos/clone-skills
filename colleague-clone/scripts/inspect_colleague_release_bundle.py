from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a finalized colleague-clone release bundle through one aggregated entrypoint.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to inspect.")
    parser.add_argument("--view", choices=["release", "runtime", "health", "full"], default="full")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    return parser.parse_args()


def bundle_artifact_paths(bundle_dir: Path) -> dict[str, Path]:
    return {
        "release_manifest": bundle_dir / "release_manifest.json",
        "runtime_package": bundle_dir / "runtime_package.json",
        "runtime_release_health": bundle_dir / "runtime_release_health.json",
        "runtime_smoke": bundle_dir / "runtime_smoke.json",
        "runtime_prompt_eval": bundle_dir / "runtime_prompt_eval.json",
    }


def required_artifacts_for_view(view: str) -> list[str]:
    if view == "release":
        return ["release_manifest"]
    if view == "runtime":
        return ["runtime_package", "runtime_smoke", "runtime_prompt_eval"]
    if view == "health":
        return ["runtime_release_health"]
    return [
        "release_manifest",
        "runtime_package",
        "runtime_release_health",
        "runtime_smoke",
        "runtime_prompt_eval",
    ]


def build_payload(bundle_dir: Path, view: str) -> dict:
    artifact_paths = bundle_artifact_paths(bundle_dir)
    availability = {name: path.exists() for name, path in artifact_paths.items()}
    issues = [
        f"missing artifact: {artifact_paths[name]}"
        for name in required_artifacts_for_view(view)
        if not availability[name]
    ]

    artifacts = {
        name: load_json(path) if availability[name] else {}
        for name, path in artifact_paths.items()
    }
    release_manifest = artifacts["release_manifest"]
    runtime_package = artifacts["runtime_package"]
    runtime_release_health_artifact = artifacts["runtime_release_health"]
    runtime_smoke_artifact = artifacts["runtime_smoke"]
    runtime_prompt_eval_artifact = artifacts["runtime_prompt_eval"]

    compare_briefs = {
        "release": dict(runtime_package.get("release", {}).get("compare_brief", {})),
        "runtime_release_health": dict(runtime_release_health_artifact.get("runtime_release_health_compare_brief", {})),
        "runtime_smoke": dict(runtime_smoke_artifact.get("runtime_smoke_compare_brief", {})),
        "runtime_prompt_eval": dict(runtime_prompt_eval_artifact.get("runtime_prompt_eval_compare_brief", {})),
    }

    payload = {
        "ok": not issues,
        "bundle_dir": str(bundle_dir),
        "view": view,
        "artifact_paths": {name: str(path) for name, path in artifact_paths.items()},
        "availability": availability,
        "issues": issues,
        "compare_briefs": compare_briefs,
    }

    if view in {"release", "full"}:
        payload["release"] = {
            "bundle": dict(release_manifest.get("bundle", {})),
            "decision": dict(release_manifest.get("runtime_release_decision", {})),
            "review": dict(release_manifest.get("runtime_release_review_brief", {})),
            "sources": dict(release_manifest.get("sources", {})),
            "evidence": dict(release_manifest.get("evidence", {})),
        }
    if view in {"runtime", "full"}:
        payload["runtime"] = {
            "bundle": dict(runtime_package.get("bundle", {})),
            "decision": dict(runtime_package.get("release", {}).get("decision", {})),
            "review": dict(runtime_package.get("release", {}).get("review_brief", {})),
            "smoke": dict(runtime_package.get("runtime_smoke_summary", {})),
            "prompt_eval": dict(runtime_package.get("runtime_prompt_eval_summary", {})),
            "contract": dict(runtime_package.get("runtime_contract_summary", {})),
            "portraits": dict(runtime_package.get("runtime_portraits_summary", {})),
        }
    if view in {"health", "full"}:
        payload["health"] = dict(runtime_release_health_artifact.get("release_health", {}))

    return payload


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    payload = build_payload(bundle_dir, args.view)

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"ok: {payload['ok']}")
        print(f"view: {payload['view']}")
        if payload["issues"]:
            print("issues:")
            for item in payload["issues"]:
                print(f"- {item}")
        health = payload.get("health", {})
        if health:
            print(f"health_decision: {health.get('decision', {}).get('decision', '')}")
            print(f"health_headline: {health.get('headline', '')}")
        compare_brief = payload.get("compare_briefs", {}).get("runtime_release_health", {})
        if compare_brief:
            print(f"runtime_release_health_compare_changed: {compare_brief.get('changed', False)}")
            print(f"runtime_release_health_compare_headline: {compare_brief.get('headline', '')}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
