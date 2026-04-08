from __future__ import annotations

import argparse
import json
from pathlib import Path

from colleague_clone_common import (
    build_release_health_summary,
    build_release_compare_report,
    build_release_manifest,
    build_runtime_package,
    build_runtime_release_health_artifact,
    build_runtime_release_health_compare_report,
    build_runtime_smoke_artifact,
    build_runtime_smoke_compare_report,
    build_runtime_smoke_report,
    build_runtime_prompt_eval_artifact,
    build_runtime_prompt_eval_compare_report,
    build_runtime_prompt_eval_report,
    build_runtime_portraits,
    load_json,
    load_previous_release_manifest,
    load_previous_runtime_release_health,
    load_previous_runtime_smoke,
    load_previous_runtime_prompt_eval,
    normalize_runtime_release_review,
    runtime_smoke_brief,
    runtime_prompt_eval_brief,
    runtime_release_decision,
    runtime_portraits_review_brief,
    summarize_runtime_portraits,
    runtime_release_review_brief,
    runtime_release_review_issues,
    summarize_runtime_contract,
    utc_now_iso,
    write_json,
)
from update_colleague_skill import append_version_history, snapshot_bundle
from validate_colleague_skill import build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a colleague-clone bundle from draft to final.")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory to promote.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).resolve()
    meta_path = bundle_dir / "meta.json"
    meta = load_json(meta_path)
    runtime_contract_path = bundle_dir / "analysis" / "runtime_contract.json"
    runtime_contract = load_json(runtime_contract_path) if runtime_contract_path.exists() else {}
    runtime_contract_summary = summarize_runtime_contract(runtime_contract) if runtime_contract else {}
    persona_profile = load_json(bundle_dir / "analysis" / "persona_profile.json")
    work_profile = load_json(bundle_dir / "analysis" / "work_profile.json")
    runtime_portraits_path = bundle_dir / "analysis" / "runtime_portraits.json"
    runtime_portraits = (
        load_json(runtime_portraits_path)
        if runtime_portraits_path.exists()
        else build_runtime_portraits(persona_profile, work_profile, runtime_contract)
    )
    runtime_portraits_summary = summarize_runtime_portraits(runtime_portraits)
    release_review = normalize_runtime_release_review(meta.get("runtime_release_review"))
    release_review_brief = runtime_release_review_brief(release_review)
    portraits_review_brief = runtime_portraits_review_brief(release_review)
    release_review_issues = runtime_release_review_issues(release_review)
    release_decision = runtime_release_decision(runtime_contract, release_review)

    if runtime_contract.get("final_contract_issues") or release_review_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "bundle_dir": str(bundle_dir),
                    "state": meta.get("state", ""),
                    "runtime_contract_final_issues": runtime_contract.get("final_contract_issues", []),
                    "runtime_contract_summary": runtime_contract_summary,
                    "runtime_portraits_summary": runtime_portraits_summary,
                    "runtime_release_review": release_review,
                    "runtime_release_review_brief": release_review_brief,
                    "runtime_portraits_review_brief": portraits_review_brief,
                    "runtime_release_decision": release_decision,
                    "runtime_release_review_issues": release_review_issues,
                },
                ensure_ascii=False,
            )
        )
        return 1

    snapshot_dir = snapshot_bundle(bundle_dir)
    meta["state"] = "final_confirmed"
    meta["updated_at"] = utc_now_iso()
    meta["finalized_at"] = utc_now_iso()
    write_json(meta_path, meta)

    report = build_report(
        bundle_dir,
        require_final=True,
        check_release_manifest=False,
        check_runtime_package=False,
        check_runtime_smoke=False,
        check_runtime_prompt_eval=False,
    )
    if not report["ok"]:
        meta["state"] = "draft_generated"
        meta["updated_at"] = utc_now_iso()
        write_json(meta_path, meta)
        print(json.dumps(report, ensure_ascii=False))
        return 1

    append_version_history(
        bundle_dir,
        {
            "updated_at": utc_now_iso(),
            "event": "promote_final",
            "snapshot_dir": str(snapshot_dir),
        },
    )
    meta = load_json(meta_path)
    report = build_report(
        bundle_dir,
        require_final=True,
        check_release_manifest=False,
        check_runtime_package=False,
        check_runtime_smoke=False,
        check_runtime_prompt_eval=False,
    )
    provisional_release_manifest = build_release_manifest(
        bundle_dir,
        meta,
        report,
        generated_at=meta.get("finalized_at", ""),
        snapshot_dir=str(snapshot_dir),
    )
    release_manifest_path = bundle_dir / "release_manifest.json"
    provisional_runtime_package = build_runtime_package(
        bundle_dir,
        meta,
        report,
        release_manifest=provisional_release_manifest,
        release_manifest_path=str(release_manifest_path),
        generated_at=meta.get("finalized_at", ""),
    )
    runtime_package_path = bundle_dir / "runtime_package.json"
    previous_release_manifest, previous_release_manifest_path = load_previous_release_manifest(
        bundle_dir,
        preferred_snapshot_dir=str(snapshot_dir),
    )
    provisional_release_compare_report = build_release_compare_report(
        provisional_release_manifest,
        previous_release_manifest,
        current_manifest_path=str(release_manifest_path),
        previous_manifest_path=previous_release_manifest_path,
    )
    provisional_release_compare_brief = {
        "has_previous": bool(provisional_release_compare_report.get("has_previous")),
        "changed": bool(provisional_release_compare_report.get("changed")),
        "headline": str(provisional_release_compare_report.get("headline", "")).strip(),
        "items": list(provisional_release_compare_report.get("items", [])),
    }
    report["release_compare_brief"] = provisional_release_compare_brief
    provisional_runtime_package = build_runtime_package(
        bundle_dir,
        meta,
        report,
        release_manifest=provisional_release_manifest,
        release_manifest_path=str(release_manifest_path),
        generated_at=meta.get("finalized_at", ""),
    )
    runtime_smoke_report = build_runtime_smoke_report(provisional_runtime_package)
    runtime_prompt_eval_report = build_runtime_prompt_eval_report(provisional_runtime_package)
    report["runtime_smoke_summary"] = runtime_smoke_brief(runtime_smoke_report)
    report["runtime_prompt_eval_summary"] = runtime_prompt_eval_brief(runtime_prompt_eval_report)
    release_manifest = build_release_manifest(
        bundle_dir,
        meta,
        report,
        generated_at=meta.get("finalized_at", ""),
        snapshot_dir=str(snapshot_dir),
    )
    release_compare_report = build_release_compare_report(
        release_manifest,
        previous_release_manifest,
        current_manifest_path=str(release_manifest_path),
        previous_manifest_path=previous_release_manifest_path,
    )
    release_compare_brief = {
        "has_previous": bool(release_compare_report.get("has_previous")),
        "changed": bool(release_compare_report.get("changed")),
        "headline": str(release_compare_report.get("headline", "")).strip(),
        "items": list(release_compare_report.get("items", [])),
    }
    write_json(release_manifest_path, release_manifest)
    report["release_compare_brief"] = release_compare_brief
    runtime_package = build_runtime_package(
        bundle_dir,
        meta,
        report,
        release_manifest=release_manifest,
        release_manifest_path=str(release_manifest_path),
        generated_at=meta.get("finalized_at", ""),
    )
    write_json(runtime_package_path, runtime_package)
    previous_runtime_smoke, previous_runtime_smoke_path = load_previous_runtime_smoke(
        bundle_dir,
        preferred_snapshot_dir=str(snapshot_dir),
    )
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
    runtime_smoke_compare_brief = {
        "has_previous": bool(runtime_smoke_compare_report.get("has_previous")),
        "changed": bool(runtime_smoke_compare_report.get("changed")),
        "headline": str(runtime_smoke_compare_report.get("headline", "")).strip(),
        "items": list(runtime_smoke_compare_report.get("items", [])),
    }
    runtime_smoke_artifact = build_runtime_smoke_artifact(
        runtime_smoke_report,
        runtime_package_path=str(runtime_package_path),
        generated_at=meta.get("finalized_at", ""),
        compare_report=runtime_smoke_compare_report,
    )
    runtime_smoke_path = bundle_dir / "runtime_smoke.json"
    write_json(runtime_smoke_path, runtime_smoke_artifact)
    previous_runtime_prompt_eval, previous_runtime_prompt_eval_path = load_previous_runtime_prompt_eval(
        bundle_dir,
        preferred_snapshot_dir=str(snapshot_dir),
    )
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
    runtime_prompt_eval_compare_brief = {
        "has_previous": bool(runtime_prompt_eval_compare_report.get("has_previous")),
        "changed": bool(runtime_prompt_eval_compare_report.get("changed")),
        "headline": str(runtime_prompt_eval_compare_report.get("headline", "")).strip(),
        "items": list(runtime_prompt_eval_compare_report.get("items", [])),
    }
    runtime_prompt_eval_artifact = build_runtime_prompt_eval_artifact(
        runtime_prompt_eval_report,
        runtime_package_path=str(runtime_package_path),
        generated_at=meta.get("finalized_at", ""),
        compare_report=runtime_prompt_eval_compare_report,
    )
    runtime_release_health = build_release_health_summary(report)
    previous_runtime_release_health, previous_runtime_release_health_path = load_previous_runtime_release_health(
        bundle_dir,
        preferred_snapshot_dir=str(snapshot_dir),
    )
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
                "state": "final_confirmed",
                "snapshot_dir": str(snapshot_dir),
                "evidence_count": report["evidence_count"],
                "runtime_contract_summary": runtime_contract_summary,
                "runtime_portraits_summary": runtime_portraits_summary,
                "runtime_release_review": release_review,
                "runtime_release_review_brief": release_review_brief,
                "runtime_portraits_review_brief": portraits_review_brief,
                "runtime_release_decision": release_decision,
                "release_manifest_path": str(release_manifest_path),
                "release_manifest": release_manifest,
                "release_compare_report": release_compare_report,
                "release_compare_brief": release_compare_brief,
                "runtime_package_path": str(runtime_package_path),
                "runtime_package": runtime_package,
                "runtime_release_health_path": str(runtime_release_health_path),
                "runtime_release_health": runtime_release_health_artifact,
                "runtime_release_health_compare_report": runtime_release_health_compare_report,
                "runtime_release_health_compare_brief": runtime_release_health_compare_brief,
                "runtime_smoke_path": str(runtime_smoke_path),
                "runtime_smoke": runtime_smoke_artifact,
                "runtime_smoke_compare_brief": runtime_smoke_compare_brief,
                "runtime_prompt_eval_path": str(runtime_prompt_eval_path),
                "runtime_prompt_eval": runtime_prompt_eval_artifact,
                "runtime_prompt_eval_compare_brief": runtime_prompt_eval_compare_brief,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
