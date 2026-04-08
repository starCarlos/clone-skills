from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_release_health_summary,
    build_runtime_package,
    build_runtime_release_health_artifact,
    build_runtime_release_health_compare_report,
    build_runtime_smoke_artifact,
    build_runtime_smoke_compare_report,
    build_runtime_smoke_report,
    build_runtime_prompt_eval_artifact,
    build_runtime_prompt_eval_compare_report,
    build_runtime_prompt_eval_report,
    load_json,
    load_previous_runtime_release_health,
    load_previous_runtime_smoke,
    load_previous_runtime_prompt_eval,
    runtime_smoke_brief,
    runtime_prompt_eval_brief,
    write_json,
)
from validate_colleague_skill import build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a finalized runtime package for a colleague-clone bundle.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to export.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    meta_path = bundle_dir / "meta.json"
    meta = load_json(meta_path)
    if meta.get("state") != "final_confirmed":
        print(
            json.dumps(
                {
                    "ok": False,
                    "bundle_dir": str(bundle_dir),
                    "state": meta.get("state", ""),
                    "issue": "runtime package export requires a final_confirmed bundle",
                },
                ensure_ascii=False,
            )
        )
        return 1

    release_manifest_path = bundle_dir / "release_manifest.json"
    if not release_manifest_path.exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "bundle_dir": str(bundle_dir),
                    "state": meta.get("state", ""),
                    "issue": "release manifest is required before exporting the runtime package",
                },
                ensure_ascii=False,
            )
        )
        return 1

    report = build_report(
        bundle_dir,
        require_final=True,
        check_release_manifest=True,
        check_runtime_package=False,
        check_runtime_smoke=False,
        check_runtime_prompt_eval=False,
    )
    if not report["ok"]:
        print(json.dumps(report, ensure_ascii=False))
        return 1

    release_manifest = load_json(release_manifest_path)
    provisional_runtime_package = build_runtime_package(
        bundle_dir,
        meta,
        report,
        release_manifest=release_manifest,
        release_manifest_path=str(release_manifest_path),
        generated_at=meta.get("finalized_at", ""),
    )
    runtime_package_path = bundle_dir / "runtime_package.json"
    runtime_smoke_report = build_runtime_smoke_report(provisional_runtime_package)
    runtime_prompt_eval_report = build_runtime_prompt_eval_report(provisional_runtime_package)
    report["runtime_smoke_summary"] = runtime_smoke_brief(runtime_smoke_report)
    report["runtime_prompt_eval_summary"] = runtime_prompt_eval_brief(runtime_prompt_eval_report)
    runtime_package = build_runtime_package(
        bundle_dir,
        meta,
        report,
        release_manifest=release_manifest,
        release_manifest_path=str(release_manifest_path),
        generated_at=meta.get("finalized_at", ""),
    )
    write_json(runtime_package_path, runtime_package)
    previous_runtime_smoke, previous_runtime_smoke_path = load_previous_runtime_smoke(bundle_dir)
    provisional_runtime_smoke_artifact = build_runtime_smoke_artifact(
        runtime_smoke_report,
        runtime_package_path=str(runtime_package_path),
        generated_at=meta.get("finalized_at", ""),
    )
    runtime_smoke_compare_report = build_runtime_smoke_compare_report(
        provisional_runtime_smoke_artifact,
        previous_runtime_smoke,
        current_runtime_smoke_path=str(bundle_dir / "runtime_smoke.json"),
        previous_runtime_smoke_path=previous_runtime_smoke_path,
    )
    runtime_smoke_artifact = build_runtime_smoke_artifact(
        runtime_smoke_report,
        runtime_package_path=str(runtime_package_path),
        generated_at=meta.get("finalized_at", ""),
        compare_report=runtime_smoke_compare_report,
    )
    runtime_smoke_path = bundle_dir / "runtime_smoke.json"
    write_json(runtime_smoke_path, runtime_smoke_artifact)
    previous_runtime_prompt_eval, previous_runtime_prompt_eval_path = load_previous_runtime_prompt_eval(bundle_dir)
    provisional_runtime_prompt_eval_artifact = build_runtime_prompt_eval_artifact(
        runtime_prompt_eval_report,
        runtime_package_path=str(runtime_package_path),
        generated_at=meta.get("finalized_at", ""),
    )
    runtime_prompt_eval_compare_report = build_runtime_prompt_eval_compare_report(
        provisional_runtime_prompt_eval_artifact,
        previous_runtime_prompt_eval,
        current_prompt_eval_path=str(bundle_dir / "runtime_prompt_eval.json"),
        previous_prompt_eval_path=previous_runtime_prompt_eval_path,
    )
    runtime_prompt_eval_artifact = build_runtime_prompt_eval_artifact(
        runtime_prompt_eval_report,
        runtime_package_path=str(runtime_package_path),
        generated_at=meta.get("finalized_at", ""),
        compare_report=runtime_prompt_eval_compare_report,
    )
    runtime_release_health = build_release_health_summary(report)
    previous_runtime_release_health, previous_runtime_release_health_path = load_previous_runtime_release_health(bundle_dir)
    provisional_runtime_release_health_artifact = build_runtime_release_health_artifact(
        runtime_release_health,
        release_manifest_path=str(release_manifest_path),
        runtime_package_path=str(runtime_package_path),
        runtime_smoke_path=str(runtime_smoke_path),
        runtime_prompt_eval_path=str(bundle_dir / "runtime_prompt_eval.json"),
        generated_at=meta.get("finalized_at", ""),
    )
    runtime_release_health_compare_report = build_runtime_release_health_compare_report(
        provisional_runtime_release_health_artifact,
        previous_runtime_release_health,
        current_runtime_release_health_path=str(bundle_dir / "runtime_release_health.json"),
        previous_runtime_release_health_path=previous_runtime_release_health_path,
    )
    runtime_release_health_compare_brief = {
        "has_previous": bool(runtime_release_health_compare_report.get("has_previous")),
        "changed": bool(runtime_release_health_compare_report.get("changed")),
        "headline": str(runtime_release_health_compare_report.get("headline", "")).strip(),
        "items": list(runtime_release_health_compare_report.get("items", [])),
    }
    runtime_release_health_artifact = build_runtime_release_health_artifact(
        runtime_release_health,
        release_manifest_path=str(release_manifest_path),
        runtime_package_path=str(runtime_package_path),
        runtime_smoke_path=str(runtime_smoke_path),
        runtime_prompt_eval_path=str(bundle_dir / "runtime_prompt_eval.json"),
        generated_at=meta.get("finalized_at", ""),
        compare_report=runtime_release_health_compare_report,
    )
    runtime_release_health_path = bundle_dir / "runtime_release_health.json"
    write_json(runtime_release_health_path, runtime_release_health_artifact)
    runtime_prompt_eval_path = bundle_dir / "runtime_prompt_eval.json"
    write_json(runtime_prompt_eval_path, runtime_prompt_eval_artifact)
    print(
        json.dumps(
            {
                "ok": True,
                "bundle_dir": str(bundle_dir),
                "runtime_package_path": str(runtime_package_path),
                "runtime_package": runtime_package,
                "runtime_release_health_path": str(runtime_release_health_path),
                "runtime_release_health": runtime_release_health_artifact,
                "runtime_release_health_compare_report": runtime_release_health_compare_report,
                "runtime_release_health_compare_brief": runtime_release_health_compare_brief,
                "runtime_smoke_path": str(runtime_smoke_path),
                "runtime_smoke": runtime_smoke_artifact,
                "runtime_prompt_eval_path": str(runtime_prompt_eval_path),
                "runtime_prompt_eval": runtime_prompt_eval_artifact,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
